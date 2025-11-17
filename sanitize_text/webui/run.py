"""Run helpers and app factory for the web UI."""

from __future__ import annotations

import sys
import warnings

from flask import Flask

from sanitize_text.utils.nlp_resources import download_optional_models
from sanitize_text.webui import routes


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
    # Optional flag: allow `-m sanitize_text.webui --download-nlp-models`
    if "--download-nlp-models" in sys.argv:
        # Remove the flag so it doesn't leak anywhere else
        sys.argv = [a for a in sys.argv if a != "--download-nlp-models"]
        download_optional_models()
    app = create_app()
    app.run(debug=True)
