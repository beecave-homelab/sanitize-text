"""Unit tests for helper utilities in :mod:`sanitize_text.webui.routes`."""

from __future__ import annotations

import importlib
import sys


def test_group_detectors_groups_generic_and_specific(monkeypatch) -> None:
    """_group_detectors should split generic and locale-specific detectors."""
    mod = importlib.import_module("sanitize_text.webui.routes")

    def fake_get_available_detectors(locale: str) -> dict[str, str]:
        base = {
            "email": "Email",
            "phone": "Phone",
            "url": "Url",
            "markdown_url": "Markdown URL",
            "private_ip": "Private IP",
            "public_ip": "Public IP",
        }
        if locale == "en_US":
            base.update({"spacy_entities": "SpaCy", "en_only": "EN only"})
        else:
            base.update({"nl_only": "NL only", "spacy_entities": "SpaCy"})
        return base

    monkeypatch.setattr(mod, "get_available_detectors", fake_get_available_detectors)

    generic, en_specific, nl_specific = mod._group_detectors()

    assert set(generic) == {"email", "phone", "url", "markdown_url", "private_ip", "public_ip"}
    assert "spacy_entities" in en_specific or "spacy_entities" in nl_specific
    assert "en_only" in en_specific and "nl_only" in nl_specific


def test_build_locale_selections_none_and_mixed() -> None:
    """_build_locale_selections returns None or per-locale mapping."""
    mod = importlib.import_module("sanitize_text.webui.routes")

    assert mod._build_locale_selections(None) is None

    selected = ["email", "en:spacy_entities", "nl:names"]
    mapping = mod._build_locale_selections(selected)
    assert mapping is not None
    assert set(mapping["en_US"]) >= {"email", "spacy_entities"}
    assert set(mapping["nl_NL"]) >= {"email", "names"}


def test_format_results_text_combines_sections() -> None:
    """_format_results_text should emit per-locale sections."""
    mod = importlib.import_module("sanitize_text.webui.routes")

    combined = mod._format_results_text([
        {"locale": "en_US", "text": "Foo"},
        {"locale": "nl_NL", "text": "Bar"},
    ])
    assert "Results for en_US:" in combined and "Foo" in combined
    assert "Results for nl_NL:" in combined and "Bar" in combined


def test_read_uploaded_file_to_text_plain_and_pdf(tmp_path, monkeypatch) -> None:
    """_read_uploaded_file_to_text supports .txt and .pdf conversion paths."""
    mod = importlib.import_module("sanitize_text.webui.routes")

    # Plain text path
    txt = tmp_path / "x.txt"
    txt.write_text("hello", encoding="utf-8")
    assert mod._read_uploaded_file_to_text(txt) == "hello"

    # PDF path with converters patched
    pdf = tmp_path / "x.pdf"
    pdf.write_text("ignored", encoding="utf-8")

    class DummyPreconvert:
        @staticmethod
        def to_markdown(path: str) -> str:  # noqa: ARG001 - parity with real API
            return "md text"

    def fake_normalize(text: str, title=None):  # noqa: ANN001, ARG001 - test shim
        return "normalized"

    # Patch module-level references used within function
    monkeypatch.setattr(mod, "preconvert", DummyPreconvert)
    monkeypatch.setattr(
        sys.modules["sanitize_text.utils.normalize"],
        "normalize_pdf_text",
        fake_normalize,
        raising=False,
    )

    assert mod._read_uploaded_file_to_text(pdf) == "normalized"
