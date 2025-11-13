"""Optional NLP resource setup utilities.

This module provides helpers to download optional NLP data when the
corresponding libraries are available. Calls are safe to run multiple
times and will never raise hard errors; failures are logged to stdout.
"""

from __future__ import annotations


def download_optional_models() -> None:
    """Download optional NLTK corpora and spaCy small models if installed.

    Notes:
        - If NLTK/spaCy aren't installed, this function prints a message and
          returns without error.
        - All download operations are best-effort; exceptions are caught and
          logged so the caller can continue normally.
    """
    # NLTK (tokenizers / taggers used by some detectors in optional flows)
    try:
        import nltk  # type: ignore
    except ImportError:
        print("NLTK not installed; skipping corpus download.")
    else:  # pragma: no cover - download side effects
        try:
            nltk.download("punkt", quiet=True)
            nltk.download("averaged_perceptron_tagger", quiet=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: Could not download NLTK data: {exc}")

    # spaCy (small language models for optional entity detectors)
    try:
        import spacy  # type: ignore
    except ImportError:
        print("spaCy not installed; skipping model download.")
        return

    spacy_models = ["en_core_web_sm", "nl_core_news_sm"]
    for model in spacy_models:  # pragma: no cover - download side effects
        try:
            spacy.load(model)
            print(f"spaCy model {model} already available")
        except OSError:
            try:
                print(f"Downloading spaCy model {model}…")
                spacy.cli.download(model)
                print(f"Successfully downloaded {model}")
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: Could not download spaCy model {model}: {exc}")
