"""Tests for :mod:`sanitize_text.webui.run` entry behavior."""

from __future__ import annotations

import runpy
import sys
import types
from types import SimpleNamespace


def test_run_module_download_flag_triggers_download(monkeypatch) -> None:
    """Running module as __main__ with flag triggers NLP model download.

    We stub Flask and routes to avoid importing the real web stack and starting a server.
    """
    # Record calls
    calls: dict[str, int] = {"download": 0, "run": 0}

    class DummyFlask:
        def __init__(self, name: str) -> None:  # noqa: ARG002 - parity with real API
            pass

        def run(self, debug: bool = False) -> None:  # noqa: FBT001 - test shim
            calls["run"] += 1

        # Provide a no-op route decorator to be resilient if real routes are used
        def route(self, *args, **kwargs):  # noqa: D401, ANN001 - simple stub
            def decorator(func):
                return func

            return decorator

    # Provide dummy flask module
    monkeypatch.setitem(sys.modules, "flask", SimpleNamespace(Flask=DummyFlask))

    # Provide dummy routes to avoid importing real app routes
    routes_mod = types.ModuleType("sanitize_text.webui.routes")
    routes_mod.init_routes = lambda app: app  # type: ignore[attr-defined]
    sys.modules["sanitize_text.webui.routes"] = routes_mod

    # Provide dummy nlp_resources module so import in run.py binds this function
    def fake_download() -> None:
        calls["download"] += 1

    monkeypatch.setitem(
        sys.modules,
        "sanitize_text.utils.nlp_resources",
        SimpleNamespace(download_optional_models=fake_download),
    )

    # Prepare argv with the download flag
    old_argv = sys.argv[:]
    sys.argv = ["-m", "sanitize_text.webui.run", "--download-nlp-models"]
    try:
        runpy.run_module("sanitize_text.webui.run", run_name="__main__")
    finally:
        sys.argv = old_argv
        sys.modules.pop("flask", None)
        sys.modules.pop("sanitize_text.webui.routes", None)
        sys.modules.pop("sanitize_text.utils.nlp_resources", None)

    assert calls["download"] == 1
    assert calls["run"] == 1
