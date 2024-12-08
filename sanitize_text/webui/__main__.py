"""Main entry point for the sanitize-text webui."""

from .run import download_required_models, create_app

def main():
    """Main entry point for the webui."""
    download_required_models()
    app = create_app()
    app.run(debug=True)

if __name__ == '__main__':
    main() 