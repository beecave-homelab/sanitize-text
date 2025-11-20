"""Entry point for the sanitize-text web UI.

This module provides a ``main`` function so the web interface can be
invoked consistently via console scripts and PDM scripts, mirroring the
CLI entry point.
"""

from __future__ import annotations

from sanitize_text.webui.run import create_app, download_optional_models


def main() -> None:
    """Run the web UI development server.

    Downloads optional NLP models (if available), creates the Flask
    application, and starts it in debug mode.
    """
    download_optional_models()
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    main()
