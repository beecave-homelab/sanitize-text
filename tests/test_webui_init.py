"""Tests for :mod:`sanitize_text.webui.__init__` application factory."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


def test_create_app_calls_init_routes(monkeypatch) -> None:
    """App factory should instantiate Flask and call init_routes within app context."""
    calls = {"init_routes": 0, "ctx_enter": 0, "ctx_exit": 0}

    class DummyCtx:
        def __enter__(self):  # noqa: D401 - minimal stub
            calls["ctx_enter"] += 1
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401 - minimal stub
            calls["ctx_exit"] += 1
            return False

    class DummyFlask:
        def __init__(self, name: str) -> None:  # noqa: ARG002 - parity with real API
            self.name = name

        def app_context(self) -> DummyCtx:
            return DummyCtx()

    def init_routes(app) -> None:  # noqa: ANN001 - simple stub
        assert isinstance(app, DummyFlask)
        calls["init_routes"] += 1

    # Provide stubs before importing the module under test
    monkeypatch.setitem(sys.modules, "flask", SimpleNamespace(Flask=DummyFlask))
    monkeypatch.setitem(
        sys.modules, "sanitize_text.webui.routes", SimpleNamespace(init_routes=init_routes)
    )

    mod = importlib.import_module("sanitize_text.webui")

    app = mod.create_app()

    assert isinstance(app, DummyFlask)
    assert calls == {"init_routes": 1, "ctx_enter": 1, "ctx_exit": 1}

    # Cleanup
    sys.modules.pop("flask", None)
    sys.modules.pop("sanitize_text.webui.routes", None)
