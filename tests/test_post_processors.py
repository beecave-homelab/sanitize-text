"""Tests for :mod:`sanitize_text.utils.post_processors`."""

from __future__ import annotations

import re
from types import SimpleNamespace

from sanitize_text.utils.filth import MarkdownUrlFilth
from sanitize_text.utils.post_processors import HashedPIIReplacer


def test_hashed_replacer_assigns_deterministic_placeholders() -> None:
    """Same input yields stable placeholders; type names are uppercased."""
    replacer = HashedPIIReplacer(modulus=10000)  # width 4

    class FakeFilth:
        def __init__(self, ftype: str, text: str) -> None:
            self.type = ftype
            self.text = text
            self.replacement_string = ""

    a1 = FakeFilth("name", "John Doe")
    a2 = FakeFilth("name", "John Doe")  # duplicate should reuse mapping
    b = FakeFilth("location", "Amsterdam")

    out = replacer.process_filth([a1, a2, b])

    assert out[0].replacement_string == out[1].replacement_string
    assert re.fullmatch(r"NAME-\d{4}", out[0].replacement_string)
    assert re.fullmatch(r"LOCATION-\d{4}", out[2].replacement_string)


def test_hashed_replacer_detects_urlish_text() -> None:
    """URL-like text should get URL placeholder type regardless of filth.type."""
    replacer = HashedPIIReplacer(modulus=1000)  # width 3

    class FakeFilth:
        def __init__(self, ftype: str, text: str) -> None:
            self.type = ftype
            self.text = text
            self.replacement_string = ""

    urlish = FakeFilth("name", "https://example.com/x")
    out = replacer.process_filth([urlish])

    assert re.fullmatch(r"URL-\d{3}", out[0].replacement_string)


def test_markdown_url_filth_is_preserved_in_placeholder() -> None:
    """MarkdownUrlFilth should render as [text](PLACEHOLDER) with correct brackets."""
    replacer = HashedPIIReplacer(modulus=1000)

    md = MarkdownUrlFilth(beg=0, end=10, text="http://x", link_text="Click", bracket_pairs=2)
    other = SimpleNamespace(type="markdown_url", text="[x](http://y)", replacement_string="")

    out = replacer.process_filth([md, other])

    # md gets double brackets
    assert re.fullmatch(r"\[\[Click\]\]\(URL-\d{3}\)", out[0].replacement_string)
    # other is treated by type==markdown_url branch and not by isinstance, so uppercase rule applies
    assert re.fullmatch(r"URL-\d{3}", out[1].replacement_string)


def test_sha256_algorithm_supported_and_width_min_3() -> None:
    """When using sha256 and modulus<1000, width remains at least 3 digits."""
    replacer = HashedPIIReplacer(algorithm="sha256", modulus=10)

    class FakeFilth:
        def __init__(self, ftype: str, text: str) -> None:
            self.type = ftype
            self.text = text
            self.replacement_string = ""

    f = FakeFilth("organization", "ACME")
    out = replacer.process_filth([f])

    assert re.fullmatch(r"ORGANIZATION-\d{3}", out[0].replacement_string)
