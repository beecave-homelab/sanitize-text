#!/usr/bin/env python3
"""pdf2md — Convert PDFs to Markdown using different backends.

Author: elvee
Date: 2025-11-06.
"""

import pathlib

import click
import pymupdf4llm
from markitdown import MarkItDown


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "input_file", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path)
)
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=pathlib.Path),
    help="Output Markdown file (default: same name as input with .md extension)."
)
@click.option(
    "--images",
    is_flag=True,
    help="Extract and reference images in the Markdown output (pymupdf4llm backend only)."
)
@click.option(
    "--dpi",
    default=150,
    show_default=True,
    help="DPI for extracted images if --images is enabled (pymupdf4llm backend only)."
)
@click.option(
    "--backend",
    type=click.Choice(["markitdown", "pymupdf4llm"], case_sensitive=False),
    default="markitdown",
    show_default=True,
    help="Backend to use for PDF to Markdown conversion."
)
def pdf2md(
    input_file: pathlib.Path,
    output: pathlib.Path | None,
    images: bool,
    dpi: int,
    backend: str,
) -> None:
    """Convert a PDF file to Markdown using the selected backend."""
    click.secho(f"📄 Processing: {input_file}", fg="cyan")

    output_path = output or input_file.with_suffix(".md")

    # Convert PDF to Markdown
    if backend.lower() == "pymupdf4llm":
        md_text = pymupdf4llm.to_markdown(
            str(input_file),
            write_images=images,
            dpi=dpi,
        )
    else:
        converter = MarkItDown()
        result = converter.convert(str(input_file))
        md_text = result.markdown

    # Write output
    output_path.write_text(md_text, encoding="utf-8")

    click.secho(f"✅ Saved Markdown → {output_path}", fg="green", bold=True)


if __name__ == "__main__":
    pdf2md()
