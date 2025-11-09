"""Flask application factory for the sanitize-text web UI."""

from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        The configured Flask application instance.
    """
    app = Flask(__name__)
    with app.app_context():
        from .routes import init_routes

        init_routes(app)
    return app
