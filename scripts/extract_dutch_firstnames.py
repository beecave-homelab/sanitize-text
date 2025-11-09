#!/usr/bin/env python3
"""Extract Dutch first names from the SVB q05a dataset.

The script downloads the q05a file, parses it into a DataFrame, extracts the
`name` column, deduplicates values, and writes a JSON file that can be used as
a PII dictionary for first names.
"""

from __future__ import annotations

import io
import json
import unicodedata
from pathlib import Path

import click
import pandas as pd
import requests

DEFAULT_URL = (
    "https://www.hackdeoverheid.nl/wp-content/uploads/sites/10/2014/05/q05a.txt"
)
DEFAULT_OUTPUT = Path("sanitize_text/data/nl_entities/names.json")


def download_file(url: str, timeout: int = 30) -> bytes:
    """Download the contents of a URL as bytes.

    Args:
        url: The URL to download.
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        The raw response body as a bytes object.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.content


def detect_encoding_and_read_bytes(raw: bytes) -> str:
    """Decode bytes into a string using a best-effort encoding strategy.

    The function tries UTF-8, Latin-1, and CP1252 before falling back to
    UTF-8 with replacement characters.

    Args:
        raw: The input bytes to decode.

    Returns:
        A decoded string representation of the input bytes.
    """
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_dataframe_from_text(text: str) -> pd.DataFrame:
    """Parse the q05a text file into a pandas DataFrame.

    The q05a dataset has five semicolon-separated columns without a header:
    sex; year; month; name; count.

    Args:
        text: The raw text content of the q05a file.

    Returns:
        A pandas DataFrame with at least five columns and, if possible,
        the column names ['sex', 'year', 'month', 'name', 'count'].
    """
    try:
        df = pd.read_csv(
            io.StringIO(text),
            sep=";",
            header=None,
            names=["sex", "year", "month", "name", "count"],
            engine="python",
        )
        if df.shape[1] == 5:
            return df
    except Exception:
        # Fall back to a naive parser; this should not normally be needed.
        pass

    df_fallback = pd.read_csv(
        io.StringIO(text),
        sep=";",
        header=None,
        engine="python",
    )
    return df_fallback


def normalize_name(name: str) -> str:
    """Normalize a single name value.

    The normalization trims whitespace, removes surrounding quotes, applies
    Unicode NFC normalization, and collapses internal whitespace.

    Args:
        name: The raw name value.

    Returns:
        A cleaned string representing the normalized name.
    """
    result = name.strip()
    if (result.startswith('"') and result.endswith('"')) or (
        result.startswith("'") and result.endswith("'")
    ):
        result = result[1:-1].strip()
    result = unicodedata.normalize("NFC", result)
    return " ".join(result.split())


def dedupe_preserve_case(names: list[str]) -> list[str]:
    """Deduplicate name values case-insensitively.

    The first occurrence of a specific case-insensitive name is preserved and
    the final result list is sorted in a case-insensitive way.

    Args:
        names: The list of (possibly duplicate) name strings.

    Returns:
        A sorted list of unique name strings.
    """
    seen: dict[str, str] = {}
    result: list[str] = []

    for item in names:
        key = item.casefold()
        if key not in seen:
            seen[key] = item
            result.append(item)

    return sorted(result, key=lambda value: value.casefold())


def to_filth_records(names: list[str]) -> list[dict[str, str]]:
    """Convert a list of names to sanitize_text-compatible records.

    Each name is wrapped in a dictionary with keys `match` and `filth_type`.

    Args:
        names: A list of unique name strings.

    Returns:
        A list of dictionaries with the structure
        `{"match": <name>, "filth_type": "name"}`.
    """
    return [{"match": name, "filth_type": "name"} for name in names]


@click.command()
@click.option(
    "--url",
    "-u",
    default=DEFAULT_URL,
    show_default=True,
    help="URL of the q05a dataset (SVB first names).",
)
@click.option(
    "--out-path",
    "-o",
    type=click.Path(path_type=Path),
    default=DEFAULT_OUTPUT,
    show_default=True,
    help="Path to the JSON output file.",
)
@click.option(
    "--sample",
    is_flag=True,
    help="Show a preview of extracted names and exit without writing a file.",
)
def main(url: str, out_path: Path, sample: bool) -> None:
    """Extract unique Dutch first names and write them to a JSON file.

    The data is fetched from the provided `url`, parsed as q05a, and converted
    into a list of records in the format:

        {"match": "<name>", "filth_type": "name"}

    Args:
        url: The URL from which to download the q05a dataset.
        out_path: Filesystem path to the JSON output file.
        sample: Whether to only print a preview of the records instead of
            writing a file to disk.
    """
    click.echo(f"Downloading dataset from: {url}")
    raw_bytes = download_file(url)
    text = detect_encoding_and_read_bytes(raw_bytes)

    df = load_dataframe_from_text(text)
    click.echo(f"Parsed DataFrame shape: {df.shape}, columns: {list(df.columns)}")

    if "name" in df.columns:
        click.echo("Using column 'name' as the name column.")
        series = df["name"].astype(str)
    else:
        click.echo(
            "Warning: 'name' column not found, falling back to the first column.",
            err=True,
        )
        series = df.iloc[:, 0].astype(str)

    cleaned = (
        series.dropna()
        .map(normalize_name)
        .loc[lambda s: (s.str.len() > 0) & (~s.str.match(r"^\\d+$"))]
    )

    names = dedupe_preserve_case(cleaned.tolist())
    click.echo(f"Unique names extracted: {len(names)}")

    records = to_filth_records(names)

    if sample:
        click.echo("Sample (first 25 records):")
        for record in records[:25]:
            click.echo(f"- {record}")
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=4)

    click.echo(f"Saved {len(records)} records to {out_path}")


if __name__ == "__main__":
    main()
