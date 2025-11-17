"""Endpoint tests for :mod:`sanitize_text.webui.routes` with patched deps."""

from __future__ import annotations

import importlib
import io

from flask import Flask


def _make_app_with_patches():
    mod = importlib.import_module("sanitize_text.webui.routes")

    # Patch lightweight render_template and send_file
    mod.render_template = lambda *a, **k: "OK"  # type: ignore[assignment]

    # Patch detector grouping to be simple and deterministic
    def fake_get_available_detectors(locale: str) -> dict[str, str]:  # noqa: ARG001
        return {
            "email": "Email",
            "phone": "Phone",
            "spacy_entities": "SpaCy",
        }

    mod.get_available_detectors = fake_get_available_detectors  # type: ignore[assignment]

    # Patch scrubber to avoid heavy dependencies
    class DummyScrubber:
        def clean(self, text: str) -> str:  # noqa: D401
            return f"CLEAN:{text}"

    mod.setup_scrubber = lambda *a, **k: DummyScrubber()  # type: ignore[assignment]
    mod.cleanup_output = lambda t: t  # type: ignore[assignment]
    mod.collect_filth = lambda *a, **k: {"en_US": []}  # type: ignore[assignment]

    # Patch get_writer to a simple file writer
    class DummyWriter:
        def write(self, text: str, output: str, **kwargs):  # noqa: ANN001, D401
            with open(output, "w", encoding="utf-8") as f:
                f.write(text)

    mod.get_writer = lambda fmt: DummyWriter()  # type: ignore[assignment,unused-argument]

    app = Flask(__name__)
    mod.init_routes(app)
    return app


def test_index_route_ok():
    """GET / should render a page."""
    app = _make_app_with_patches()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"OK" in resp.data


def test_process_route_basic_json():
    """POST /process returns JSON with results list."""
    app = _make_app_with_patches()
    client = app.test_client()
    resp = client.post(
        "/process",
        json={"text": "hello", "locale": "en_US", "detectors": ["email"], "verbose": False},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and "results" in data and isinstance(data["results"], list)


def test_export_txt_download():
    """POST /export returns an attachment with text/plain mimetype when txt requested."""
    app = _make_app_with_patches()
    client = app.test_client()
    resp = client.post(
        "/export",
        json={
            "text": "hello",
            "locale": "en_US",
            "detectors": ["email"],
            "cleanup": True,
            "output_format": "txt",
        },
    )
    assert resp.status_code == 200
    # Should be an attachment
    assert resp.mimetype == "text/plain"


def test_process_file_txt_upload():
    """POST /process-file with a .txt upload returns JSON results."""
    app = _make_app_with_patches()
    client = app.test_client()

    data = {
        "file": (io.BytesIO(b"hello"), "input.txt"),
        "locale": "en_US",
    }
    resp = client.post("/process-file", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload and "results" in payload


def test_process_route_verbose_includes_filth():
    """POST /process with verbose should include an empty filth list per locale."""
    app = _make_app_with_patches()
    client = app.test_client()
    resp = client.post(
        "/process",
        json={"text": "hello", "locale": "en_US", "detectors": [], "verbose": True},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and data["results"][0].get("filth") == []


def test_download_file_pdf_output():
    """POST /download-file should return a PDF attachment when requested."""
    app = _make_app_with_patches()
    client = app.test_client()

    data = {
        "file": (io.BytesIO(b"hello"), "input.txt"),
        "output_format": "pdf",
        "font_size": "12",
    }
    resp = client.post("/download-file", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


def test_cli_preview_builds_command_for_text():
    """POST /cli-preview should return a CLI command preview for text input."""
    app = _make_app_with_patches()
    client = app.test_client()

    payload = {
        "source": "text",
        "locale": "en_US",
        "detectors": ["email", "en:name"],
        "cleanup": True,
        "verbose": False,
        "output_format": "txt",
    }
    resp = client.post("/cli-preview", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    command = data.get("command", "")
    # Basic structure and key flags should be present
    assert "sanitize-text" in command
    assert "-t" in command
    assert "-l en_US" in command
    # Locale-specific detector prefix should be normalized away
    assert "email" in command
    assert "name" in command


def test_cli_preview_builds_command_for_file_pdf():
    """POST /cli-preview should include PDF-related options for file mode."""
    app = _make_app_with_patches()
    client = app.test_client()

    payload = {
        "source": "file",
        "locale": None,
        "detectors": ["email"],
        "cleanup": False,
        "verbose": True,
        "output_format": "pdf",
        "pdf_mode": "para",
        "font_size": 14,
    }
    resp = client.post("/cli-preview", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    command = data.get("command", "")
    assert "sanitize-text" in command
    assert "-i" in command  # file mode
    # Multi-locale default should not require -l flag when locale is omitted
    assert "-l" not in command
    # PDF-specific flags
    assert "--output-format pdf" in command
    assert "--pdf-mode para" in command
    assert "--font-size 14" in command
    # Other flags derived from booleans
    assert "--no-cleanup" in command
    assert "-v" in command
