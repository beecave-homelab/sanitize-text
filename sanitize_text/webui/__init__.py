"""Flask application factory for the sanitize-text web UI."""

import logging

from flask import Flask


def create_app(*, verbose: bool = False) -> Flask:
    """Create and configure the Flask application.

    Args:
        verbose: Whether to emit scrub details to stdout for every request.

    Returns:
        The configured Flask application instance.
    """
    app = Flask(__name__)
    if not hasattr(app, "config"):
        app.config = {}
    app.config["SANITIZE_VERBOSE"] = verbose
    if verbose:
        app_logger = getattr(app, "logger", None)
        if app_logger is not None:
            app_logger.setLevel(logging.INFO)
            for handler in getattr(app_logger, "handlers", []) or []:
                handler.setLevel(logging.INFO)
    with app.app_context():
        from .routes import init_routes

        init_routes(app)
    return app
