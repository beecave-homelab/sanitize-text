"""Tests for :mod:`sanitize_text.utils.nlp_resources`."""

from __future__ import annotations

import builtins
import logging
import sys
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest


def _import_blocker(block_names: set[str]) -> Callable[..., Any]:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 - test shim
        if name in block_names:
            raise ImportError(f"Blocked import for testing: {name}")
        return real_import(name, *args, **kwargs)

    return fake_import


def test_download_optional_models__when_nltk_and_spacy_missing(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gracefully skip when optional deps are not installed."""
    from sanitize_text.utils import nlp_resources

    # Block imports only for nltk and spacy within the call
    monkeypatch.setattr(builtins, "__import__", _import_blocker({"nltk", "spacy"}))

    with caplog.at_level(logging.INFO):
        nlp_resources.download_optional_models()

    messages = "\n".join(caplog.messages)
    assert "NLTK not installed; skipping corpus download." in messages
    assert "spaCy not installed; skipping model download." in messages


def test_download_optional_models__nltk_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """When NLTK is present, attempt to download expected corpora."""
    from sanitize_text.utils import nlp_resources

    calls: list[str] = []

    class DummyNltk:
        @staticmethod
        def download(name: str, quiet: bool = True) -> None:  # noqa: ARG002 - parity with real API
            calls.append(name)

    # Provide fake nltk, make spacy unavailable to return early after nltk path
    monkeypatch.setitem(sys.modules, "nltk", DummyNltk())
    monkeypatch.setattr(builtins, "__import__", _import_blocker({"spacy"}))

    try:
        nlp_resources.download_optional_models()
    finally:
        sys.modules.pop("nltk", None)

    assert set(calls) == {"punkt", "averaged_perceptron_tagger"}


def test_download_optional_models__spacy_models_already_available(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When spaCy can load models, ensure we surface informative messages."""
    from sanitize_text.utils import nlp_resources

    # Fake spaCy module
    def load(model: str) -> object:  # noqa: ANN401 - test shim
        # Simulate both models being available
        assert model in {"en_core_web_sm", "nl_core_news_sm"}
        return object()

    dummy_spacy = SimpleNamespace(load=load, cli=SimpleNamespace(download=lambda model: None))

    # Ensure nltk is treated as missing to avoid download attempts
    monkeypatch.setattr(builtins, "__import__", _import_blocker({"nltk"}))
    monkeypatch.setitem(sys.modules, "spacy", dummy_spacy)  # type: ignore[assignment]

    try:
        with caplog.at_level(logging.INFO):
            nlp_resources.download_optional_models()
    finally:
        sys.modules.pop("spacy", None)

    messages = "\n".join(caplog.messages)
    assert "spaCy model en_core_web_sm already available" in messages
    assert "spaCy model nl_core_news_sm already available" in messages


def test_download_optional_models__spacy_download_on_missing_and_warn_on_failure(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trigger download when load raises OSError and warn if download fails."""
    from sanitize_text.utils import nlp_resources

    load_calls: list[str] = []
    download_calls: list[str] = []

    def load(model: str) -> object:  # noqa: ANN401 - test shim
        load_calls.append(model)
        # Make first model missing and second missing with download failure
        if model == "en_core_web_sm":
            raise OSError("model not found")
        raise OSError("missing with failure")

    def download(model: str) -> None:
        download_calls.append(model)
        if model == "nl_core_news_sm":
            raise RuntimeError("network error")

    dummy_spacy = SimpleNamespace(load=load, cli=SimpleNamespace(download=download))

    # Ensure nltk is treated as missing to avoid interacting with it here
    monkeypatch.setattr(builtins, "__import__", _import_blocker({"nltk"}))
    monkeypatch.setitem(sys.modules, "spacy", dummy_spacy)  # type: ignore[assignment]

    try:
        with caplog.at_level(logging.INFO):
            nlp_resources.download_optional_models()
    finally:
        sys.modules.pop("spacy", None)

    messages = "\n".join(caplog.messages)
    # en_core_web_sm: should attempt and report success message path
    assert "Downloading spaCy model en_core_web_sm…" in messages
    assert "Successfully downloaded en_core_web_sm" in messages
    # nl_core_news_sm: should warn on failure
    assert "Downloading spaCy model nl_core_news_sm…" in messages
    assert "Warning: Could not download spaCy model nl_core_news_sm: network error" in messages

    assert load_calls == ["en_core_web_sm", "nl_core_news_sm"]
    assert download_calls == ["en_core_web_sm", "nl_core_news_sm"]
