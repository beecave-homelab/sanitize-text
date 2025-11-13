"""Tests for package entrypoint :mod:`sanitize_text.__main__`."""

from __future__ import annotations

import runpy
import sys
from types import SimpleNamespace


def test_package_main_invokes_cli_main(monkeypatch) -> None:
    """`python -m sanitize_text` should call CLI main.

    We stub `sanitize_text.cli.main.main` to avoid importing the real CLI.
    """
    calls = {"main": 0}

    def fake_main() -> None:
        calls["main"] += 1

    # Provide stub for fully-qualified import path used in __main__
    monkeypatch.setitem(sys.modules, "sanitize_text.cli.main", SimpleNamespace(main=fake_main))

    runpy.run_module("sanitize_text", run_name="__main__")

    # Cleanup to avoid leaking stubs to other tests
    sys.modules.pop("sanitize_text.cli.main", None)

    assert calls["main"] == 1
