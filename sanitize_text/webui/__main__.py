"""Main entry point for the sanitize-text webui."""

from .run import create_app, download_optional_models


def main() -> None:
    """Main entry point for the webui."""
    download_optional_models()
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":
    main()
