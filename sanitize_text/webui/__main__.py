"""Main entry point for the sanitize-text webui."""

from .run import create_app, download_required_models


def main():
    """Main entry point for the webui."""
    download_required_models()
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":
    main()
