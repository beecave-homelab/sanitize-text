#!/usr/bin/env python3
r"""Convert a JSON file with entries into spaCy training data.

[
  { "match": "'s Gravenmoer", "filth_type": "location" },
  { "match": "Aafke", "filth_type": "name" },
  { "match": "\"AAE\" Advanced Automated Equipment B.V.", "filth_type": "organization" }
]

into a spaCy training-compatible JSON:

[
  {
    "text": "'s Gravenmoer",
    "entities": [
      { "start": 0, "end": 13, "label": "LOC" }
    ]
  },
  {
    "text": "Aafke",
    "entities": [
      { "start": 0, "end": 5, "label": "PERSON" }
    ]
  },
  {
    "text": "\"AAE\" Advanced Automated Equipment B.V.",
    "entities": [
      { "start": 0, "end": 43, "label": "ORG" }
    ]
  }
]

Output is saved in the SAME directory as the input file,
with '_spaCy.json' appended to the filename.
"""

import json
import sys
from pathlib import Path

# Map your filth_type values to spaCy NER labels
FILTH_TO_SPACY_LABEL = {
    "name": "PERSON",
    "location": "LOC",
    "organization": "ORG",
    "organisation": "ORG",  # handle both spellings just in case
}


def convert_to_spacy_dataset(input_path: str) -> Path:
    """Convert a JSON file with entries into spaCy training data.

    Args:
        input_path (str): Path to the input JSON file.

    Raises:
        FileNotFoundError: If the input file does not exist.

    Returns:
        Path: Path to the output spaCy training data file.
    """
    in_path = Path(input_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    # Define output path in same folder, append "_spaCy"
    output_path = in_path.with_name(f"{in_path.stem}_spaCy.json")

    # Load data
    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    training_data = []

    for i, entry in enumerate(data):
        text = entry.get("match")
        filth_type = entry.get("filth_type")

        if not text or not filth_type:
            # Skip incomplete lines
            continue

        label = FILTH_TO_SPACY_LABEL.get(filth_type)
        if label is None:
            # Unknown filth_type → skip, or you could log/print a warning
            # print(f"Skipping entry {i}: unknown filth_type={filth_type!r}")
            continue

        example = {
            "text": text,
            "entities": [
                {
                    "start": 0,
                    "end": len(text),
                    "label": label,
                }
            ],
        }
        training_data.append(example)

    # Save output
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved spaCy training data to: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_to_spacy.py <input_file.json>")
        sys.exit(1)

    input_file = sys.argv[1]
    convert_to_spacy_dataset(input_file)
