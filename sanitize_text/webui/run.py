"""Run helpers and app factory for the web UI."""

import warnings

from flask import Flask

from . import routes


def download_optional_models() -> None:
    """Download optional NLP resources when the dependencies are available."""
    try:
        import nltk  # type: ignore
    except ImportError:
        print("NLTK not installed; skipping corpus download.")
    else:  # pragma: no cover - download side effects
        try:
            nltk.download("punkt", quiet=True)
            nltk.download("averaged_perceptron_tagger", quiet=True)
        except Exception as exc:
            print(f"Warning: Could not download NLTK data: {exc}")

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
            except Exception as exc:
                print(f"Warning: Could not download spaCy model {model}: {exc}")


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        The configured Flask application instance.
    """
    app = Flask(__name__)
    routes.init_routes(app)
    return app


# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

if __name__ == "__main__":
    download_optional_models()
    app = create_app()
    app.run(debug=True)
