"""Click-based entry point for the sanitize-text web UI.

This module exposes a :func:`main` function suitable for console scripts
so the web interface can be started via ``sanitize-text-webui`` with
configurable host, port, debug mode, and optional NLP model download.
"""

from __future__ import annotations

import click

from sanitize_text.webui.run import create_app, download_optional_models

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host interface to bind the development server to.",
)
@click.option(
    "--port",
    type=int,
    default=5000,
    show_default=True,
    help="Port to run the development server on.",
)
@click.option(
    "--debug/--no-debug",
    default=True,
    show_default=True,
    help="Enable or disable Flask debug mode.",
)
@click.option(
    "--download-nlp-models/--no-download-nlp-models",
    default=True,
    show_default=True,
    help=(
        "Download optional NLP resources (NLTK corpora and spaCy small models) "
        "before starting the server."
    ),
)
def main(host: str, port: int, debug: bool, download_nlp_models: bool) -> None:
    """Run the web UI development server.

    This command starts a Flask development server hosting the
    ``sanitize-text`` web interface. By default it downloads optional NLP
    resources on startup and runs with debug mode enabled.

    Args:
        host: Host interface to bind the development server to.
        port: TCP port to listen on.
        debug: Whether to enable Flask debug mode.
        download_nlp_models: Whether to download optional NLP resources
            before starting the server.
    """
    if download_nlp_models:
        download_optional_models()

    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    main(standalone_mode=True)
