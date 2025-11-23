"""Tests for :mod:`sanitize_text.webui` entry behavior."""

from __future__ import annotations

import importlib
import runpy
import sys
from types import SimpleNamespace

from click.testing import CliRunner


def test_webui_main_runs_app_and_downloads(monkeypatch) -> None:
    """`python -m sanitize_text.webui` should download NLP models and run app."""
    calls = {"download": 0, "run": 0, "create": []}

    class DummyFlask:
        def run(self, debug: bool = False) -> None:  # noqa: FBT001 - test shim
            calls["run"] += 1

    def create_app(*, verbose: bool = False) -> DummyFlask:
        calls["create"].append(verbose)
        return DummyFlask()

    def download_optional_models() -> None:
        calls["download"] += 1

    # Provide a dummy webui.run module with the two functions imported in __main__
    monkeypatch.setitem(
        sys.modules,
        "sanitize_text.webui.run",
        SimpleNamespace(create_app=create_app, download_optional_models=download_optional_models),
    )

    runpy.run_module("sanitize_text.webui.__main__", run_name="__main__")

    # Cleanup
    sys.modules.pop("sanitize_text.webui.run", None)

    assert calls["download"] == 1
    assert calls["run"] == 1
    assert calls["create"] == [False]


def test_webui_click_main_downloads_and_runs_with_defaults(monkeypatch) -> None:
    """sanitize_text.webui.main should download models and run app with defaults."""
    mod = importlib.import_module("sanitize_text.webui.main")

    calls = {"download": 0, "run": [], "create": []}

    class DummyApp:
        def run(self, host: str, port: int, debug: bool = False) -> None:  # noqa: FBT001
            calls["run"].append({"host": host, "port": port, "debug": debug})

    def download_optional_models() -> None:
        calls["download"] += 1

    def create_app(*, verbose: bool = False) -> DummyApp:
        calls["create"].append(verbose)
        return DummyApp()

    monkeypatch.setattr(mod, "download_optional_models", download_optional_models)
    monkeypatch.setattr(mod, "create_app", create_app)

    runner = CliRunner()
    result = runner.invoke(mod.main, [])

    assert result.exit_code == 0
    assert calls["download"] == 1
    assert calls["run"] == [{"host": "127.0.0.1", "port": 5000, "debug": True}]
    assert calls["create"] == [False]


def test_webui_click_main_respects_host_port_debug_download_and_verbose(monkeypatch) -> None:
    """CLI options should control core flags including verbose and download behavior."""
    mod = importlib.import_module("sanitize_text.webui.main")

    calls = {"download": 0, "run": [], "create": []}

    class DummyApp:
        def run(self, host: str, port: int, debug: bool = False) -> None:  # noqa: FBT001
            calls["run"].append({"host": host, "port": port, "debug": debug})

    def download_optional_models() -> None:
        calls["download"] += 1

    def create_app(*, verbose: bool = False) -> DummyApp:
        calls["create"].append(verbose)
        return DummyApp()

    monkeypatch.setattr(mod, "download_optional_models", download_optional_models)
    monkeypatch.setattr(mod, "create_app", create_app)

    runner = CliRunner()
    result = runner.invoke(
        mod.main,
        [
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--no-debug",
            "--no-download-nlp-models",
            "--verbose",
        ],
    )

    assert result.exit_code == 0
    # download should not be called when --no-download-nlp-models is used
    assert calls["download"] == 0
    assert calls["run"] == [{"host": "0.0.0.0", "port": 8000, "debug": False}]
    assert calls["create"] == [True]
