"""UI layout regression tests for the Flask web UI."""

from __future__ import annotations

import importlib
from pathlib import Path

from flask import Flask


def _build_app(monkeypatch) -> Flask:
    """Create an app instance with lightweight detector patches."""

    mod = importlib.import_module("sanitize_text.webui.routes")

    def fake_get_available_detectors(locale: str) -> dict[str, str]:  # noqa: ARG001
        return {
            "email": "Email",
            "phone": "Phone",
            "url": "URL",
            "spacy_entities": "SpaCy",
        }

    monkeypatch.setattr(mod, "get_available_detectors", fake_get_available_detectors)

    project_root = Path(__file__).resolve().parents[1]
    template_folder = project_root / "sanitize_text" / "webui" / "templates"
    static_folder = project_root / "sanitize_text" / "webui" / "static"
    app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
    mod.init_routes(app)
    return app


def test_index_renders_flow_steps_and_cli_preview(monkeypatch) -> None:
    """The landing page should highlight the flow and CLI wrapper."""

    app = _build_app(monkeypatch)
    response = app.test_client().get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    assert html.count('data-testid="flow-step-card"') >= 3
    assert 'data-testid="cli-preview-panel"' in html


def test_index_exposes_accessible_theme_toggle(monkeypatch) -> None:
    """The dark-mode toggle should be exposed with accessibility attributes."""

    app = _build_app(monkeypatch)
    response = app.test_client().get("/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    assert 'data-testid="theme-toggle"' in html
    assert 'aria-pressed' in html
    assert 'data-testid="workspace-grid"' in html
