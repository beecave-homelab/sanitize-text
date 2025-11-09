#!/usr/bin/env python3
"""Train simple spaCy NER models on your PII entity datasets.

Directory layout (relative to this script):

project_root/
├── sanitize_text/
│   ├── data/
│   │   ├── en_entities/
│   │   │   ├── names_spaCy.json
│   │   │   ├── locations_spaCy.json
│   │   │   └── organizations_spaCy.json
│   │   └── nl_entities/
│   │       ├── names_spaCy.json
│   │       ├── cities_spaCy.json
│   │       └── organizations_spaCy.json
│   └── models/
└── scripts/
    └── train_spacy_ner.py

Usage:
  python scripts/train_spacy_ner.py --lang all
  python scripts/train_spacy_ner.py --lang en --n-iter 30 --batch-size 32
"""

import json
import random
from pathlib import Path

import click
import spacy
from spacy.training import Example
from spacy.util import minibatch

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_ROOT / "sanitize_text" / "data"
MODELS_ROOT = PROJECT_ROOT / "sanitize_text" / "models"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_spacy_json_dataset(lang_code: str) -> tuple[list[Example], list[str]]:
    """Load spaCy JSON dataset for a given language.

    Args:
        lang_code: Language code ("en" or "nl")

    Returns:
        Tuple of (examples, labels)

    Raises:
        ValueError: If lang_code is not "en" or "nl"
        FileNotFoundError: If data directory is not found
    """
    if lang_code == "en":
        data_dir = DATA_ROOT / "en_entities"
    elif lang_code == "nl":
        data_dir = DATA_ROOT / "nl_entities"
    else:
        raise ValueError(f"Unsupported language code: {lang_code}")

    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    examples = []
    labels = set()
    nlp_blank = spacy.blank(lang_code)

    for path in sorted(data_dir.glob("*_spaCy.json")):
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            text = entry.get("text")
            ents = entry.get("entities", [])
            if not text or not ents:
                continue

            entities = [(ent["start"], ent["end"], ent["label"]) for ent in ents]
            for _, _, label in entities:
                labels.add(label)

            doc = nlp_blank.make_doc(text)
            examples.append(Example.from_dict(doc, {"entities": entities}))

    if not examples:
        raise ValueError(f"No training examples found in {data_dir}")

    return examples, sorted(labels)


# ---------------------------------------------------------------------------
# Training logic
# ---------------------------------------------------------------------------

def train_ner(
    lang_code: str,
    n_iter: int = 20,
    batch_size: int = 16,
    dropout: float = 0.2,
) -> None:
    """Train a small spaCy NER model for a given language."""
    click.echo(f"\n=== Training NER model for language: {lang_code} ===")

    examples, labels = load_spacy_json_dataset(lang_code)
    click.echo(f"Loaded {len(examples)} examples | Labels: {labels}")

    random.shuffle(examples)
    split = int(len(examples) * 0.9)
    train_examples = examples[:split]
    dev_examples = examples[split:]

    click.echo(f"Train: {len(train_examples)}, Dev: {len(dev_examples)}")

    nlp = spacy.blank(lang_code)
    ner = nlp.add_pipe("ner")

    for label in labels:
        ner.add_label(label)

    with nlp.disable_pipes(*[p for p in nlp.pipe_names if p != "ner"]):
        optimizer = nlp.begin_training()

        for itn in range(1, n_iter + 1):
            random.shuffle(train_examples)
            losses = {}

            for batch in minibatch(train_examples, size=batch_size):
                nlp.update(batch, drop=dropout, sgd=optimizer, losses=losses)

            click.echo(f"Iter {itn:02d} | Losses: {losses}")

    if dev_examples:
        with nlp.select_pipes(enable="ner"):
            scores = nlp.evaluate(dev_examples)
        click.echo(f"\nDev scores for {lang_code}:\n{scores}")

    out_dir = MODELS_ROOT / f"{lang_code}_pii_ner"
    out_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(out_dir)
    click.echo(f"\n✅ Saved {lang_code} model to: {out_dir}")


# ---------------------------------------------------------------------------
# CLI (Click)
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--lang",
    type=click.Choice(["en", "nl", "all"], case_sensitive=False),
    default="all",
    help="Which language model(s) to train.",
)
@click.option(
    "--n-iter",
    type=int,
    default=20,
    help="Number of training iterations (epochs).",
)
@click.option(
    "--batch-size",
    type=int,
    default=16,
    help="Batch size for training.",
)
@click.option(
    "--dropout",
    type=float,
    default=0.2,
    help="Dropout rate during training.",
)
def main(lang: str, n_iter: int, batch_size: int, dropout: float) -> None:
    """Train spaCy NER models for English and/or Dutch PII entities."""
    if lang in ("en", "all"):
        train_ner("en", n_iter=n_iter, batch_size=batch_size, dropout=dropout)

    if lang in ("nl", "all"):
        train_ner("nl", n_iter=n_iter, batch_size=batch_size, dropout=dropout)


if __name__ == "__main__":
    main()
