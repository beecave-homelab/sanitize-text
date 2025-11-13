"""Tests for :mod:`sanitize_text.webui.__main__` behavior."""

from __future__ import annotations

import runpy
import sys
from types import SimpleNamespace


def test_webui_main_runs_app_and_downloads(monkeypatch) -> None:
    """`python -m sanitize_text.webui` should download NLP models and run app."""
    calls = {"download": 0, "run": 0}

    class DummyFlask:
        def run(self, debug: bool = False) -> None:  # noqa: FBT001 - test shim
            calls["run"] += 1

    def create_app() -> DummyFlask:
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
