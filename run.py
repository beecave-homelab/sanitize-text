#!venv/bin/python3

import warnings
import nltk
import spacy
from scrub_webui import create_app

def download_required_models():
    """Download all required NLTK and spaCy models."""
    # Download NLTK data
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
    except Exception as e:
        print(f"Warning: Could not download NLTK data: {str(e)}")

    # Download spaCy models
    spacy_models = ['en_core_web_sm', 'nl_core_news_sm']
    for model in spacy_models:
        try:
            spacy.load(model)
            print(f"SpaCy model {model} already downloaded")
        except OSError:
            try:
                print(f"Downloading SpaCy model {model}...")
                spacy.cli.download(model)
                print(f"Successfully downloaded {model}")
            except Exception as e:
                print(f"Warning: Could not download SpaCy model {model}: {str(e)}")

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")

if __name__ == '__main__':
    download_required_models()
    app = create_app()
    app.run(debug=True)