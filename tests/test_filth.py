"""Tests for sanitize_text.utils.filth module."""

from __future__ import annotations

from sanitize_text.utils.filth import (
    LocationFilth,
    MarkdownUrlFilth,
    NameFilth,
    OrganizationFilth,
    PrivateIPFilth,
    PublicIPFilth,
)


def test_filth_types() -> None:
    """Test that all filth classes have correct type attributes."""
    assert LocationFilth.type == "location"
    assert OrganizationFilth.type == "organization"
    assert NameFilth.type == "name"
    assert PrivateIPFilth.type == "private_ip"
    assert PublicIPFilth.type == "public_ip"
    assert MarkdownUrlFilth.type == "markdown_url"


def test_markdown_url_filth_initialization() -> None:
    """Test MarkdownUrlFilth initialization with custom parameters."""
    # Test basic initialization
    filth = MarkdownUrlFilth(
        beg=0,
        end=10,
        text="test",
        link_text="Example Link",
        url="https://example.com",
        bracket_pairs=2,
    )

    assert filth.link_text == "Example Link"
    assert filth.url == "https://example.com"
    assert filth.bracket_pairs == 2


def test_markdown_url_filth_default_values() -> None:
    """Test MarkdownUrlFilth with default parameter values."""
    filth = MarkdownUrlFilth(beg=0, end=4, text="test")

    assert filth.link_text == ""
    assert filth.url == ""
    assert filth.bracket_pairs == 1


def test_markdown_url_filth_bracket_pairs_validation() -> None:
    """Test that bracket_pairs is always at least 1."""
    # Test with zero (should be coerced to 1)
    filth = MarkdownUrlFilth(beg=0, end=4, text="test", bracket_pairs=0)
    assert filth.bracket_pairs == 1

    # Test with negative value (should be coerced to 1)
    filth = MarkdownUrlFilth(beg=0, end=4, text="test", bracket_pairs=-5)
    assert filth.bracket_pairs == 1

    # Test with positive value (should be preserved)
    filth = MarkdownUrlFilth(beg=0, end=4, text="test", bracket_pairs=3)
    assert filth.bracket_pairs == 3

    # Test with float value (should be converted to int)
    filth = MarkdownUrlFilth(beg=0, end=4, text="test", bracket_pairs=2.7)
    assert filth.bracket_pairs == 2


def test_filth_inheritance() -> None:
    """Test that all filth classes properly inherit from base Filth class."""
    # Test that all classes can be instantiated with basic Filth parameters
    for filth_class in [LocationFilth, OrganizationFilth, NameFilth, PrivateIPFilth, PublicIPFilth]:
        filth = filth_class(beg=0, end=4, text="test")
        assert filth.beg == 0
        assert filth.end == 4
        assert filth.text == "test"

    # Test MarkdownUrlFilth with additional parameters
    markdown_filth = MarkdownUrlFilth(beg=5, end=15, text="link text", link_text="Link", url="http://example.com")
    assert markdown_filth.beg == 5
    assert markdown_filth.end == 15
    assert markdown_filth.text == "link text"
