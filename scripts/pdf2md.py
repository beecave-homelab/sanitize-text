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
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=pathlib.Path),
    help="Output Markdown file (default: same name as input with .md extension).",
)
@click.option(
    "--images",
    is_flag=True,
    help="Extract and reference images in the Markdown output (pymupdf4llm backend only).",
)
@click.option(
    "--dpi",
    default=150,
    show_default=True,
    help="DPI for extracted images if --images is enabled (pymupdf4llm backend only).",
)
@click.option(
    "--backend",
    type=click.Choice(["markitdown", "pymupdf4llm", "all"], case_sensitive=False),
    default="pymupdf4llm",
    show_default=True,
    help=(
        "Backend to use for PDF to Markdown conversion. "
        "Use 'all' to run all backends for comparison."
    ),
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

    base_output = output or input_file.with_suffix(".md")

    # Run all backends for comparison
    if backend.lower() == "all":
        parent = base_output.parent
        stem = base_output.stem

        # PyMuPDF4LLM backend
        click.secho("🔧 Backend: pymupdf4llm", fg="yellow")
        md_text_pymupdf = pymupdf4llm.to_markdown(
            str(input_file),
            write_images=images,
            dpi=dpi,
        )
        output_path_pymupdf = parent / f"{stem}.pymupdf4llm.md"
        output_path_pymupdf.write_text(md_text_pymupdf, encoding="utf-8")
        click.secho(
            f"✅ Saved Markdown (pymupdf4llm) → {output_path_pymupdf}",
            fg="green",
            bold=True,
        )

        # MarkItDown backend
        click.secho("🔧 Backend: markitdown", fg="yellow")
        converter = MarkItDown()
        result = converter.convert(str(input_file))
        md_text_markitdown = result.markdown
        output_path_markitdown = parent / f"{stem}.markitdown.md"
        output_path_markitdown.write_text(md_text_markitdown, encoding="utf-8")
        click.secho(
            f"✅ Saved Markdown (markitdown) → {output_path_markitdown}",
            fg="green",
            bold=True,
        )

        return

    # Single-backend mode
    output_path = base_output

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

    output_path.write_text(md_text, encoding="utf-8")

    click.secho(f"✅ Saved Markdown → {output_path}", fg="green", bold=True)


if __name__ == "__main__":
    pdf2md()
