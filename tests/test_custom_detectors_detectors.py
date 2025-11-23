"""Tests for custom detector classes: URL, SharePoint, IP, CustomWord, Markdown URL.

Covers basic iteration and key heuristics to increase coverage.
"""

from __future__ import annotations

from sanitize_text.utils.custom_detectors.custom_word import CustomWordDetector
from sanitize_text.utils.custom_detectors.ip_detectors import (
    PrivateIPDetector,
    PublicIPDetector,
)
from sanitize_text.utils.custom_detectors.markdown_url_detector import (
    MarkdownUrlDetector,
)
from sanitize_text.utils.custom_detectors.sharepoint_url_detector import (
    SharePointUrlDetector,
)
from sanitize_text.utils.custom_detectors.url_detector import BareDomainDetector


def test_custom_word_detector_iter_filth_multiple() -> None:
    """CustomWordDetector yields each occurrence of the custom text."""
    det = CustomWordDetector(custom_text="Foo")
    text = "Bar Foo baz Foo"
    out = list(det.iter_filth(text))
    assert len(out) == 2
    assert all(getattr(f, "text", None) == "Foo" for f in out)


def test_custom_word_detector_early_return() -> None:
    """No custom_text or empty text yields no filth (early returns)."""
    det1 = CustomWordDetector(custom_text=None)
    det2 = CustomWordDetector(custom_text="X")
    assert list(det1.iter_filth("anything")) == []
    assert list(det2.iter_filth("")) == []


def test_markdown_url_detector_variants_and_trim() -> None:
    """MarkdownUrlDetector handles standard and double-bracket links and trims URL."""
    det = MarkdownUrlDetector()
    text = (
        "Read [link](http://example.com/path?x=1&y=2). "
        "Also [[Site]](<https://example.com/abc)> , and [[bad](mismatch)."
    )
    items = list(det.iter_filth(text))
    # First standard link
    assert any("http://example.com/path?x=1&y=2" in getattr(f, "url", "") for f in items)
    # Double-bracket link preserved and angle brackets + trailing junk trimmed
    dbl = [f for f in items if getattr(f, "bracket_pairs", 1) == 2]
    assert dbl and all("example.com/abc" in getattr(f, "url", "") for f in dbl)
    # Mismatched brackets are skipped -> only two valid matches
    assert len(items) == 2


def test_url_detector_basic_and_sharepoint_heuristics() -> None:
    """BareDomainDetector matches common URL forms and skips sharepoint fragments."""
    det = BareDomainDetector()
    text = (
        "Visit example.com/page and www.Example.com, also HTTP://foo.dev. "
        "Do not match split 'share' + 'epoint.com' when 'sharepoint' appears nearby: "
        "share epoint.com; sharepoint."
    )
    urls = [f.text.lower() for f in det.iter_filth(text)]
    assert any("example.com" in u for u in urls)
    assert any("foo.dev" in u for u in urls)
    # Ensure the share epoint.com fragment is filtered out by heuristics
    assert not any("epoint.com" == u for u in urls)


def test_url_detector_line_level_sharepoint_check() -> None:
    """When document lacks 'sharepoint' but line contains it, filter point.com."""
    det = BareDomainDetector()
    text = (
        "Some intro without the keyword.\n"
        "This line mentions sharepoint and includes point.com which should be skipped.\n"
        "Tail."
    )
    urls = [f.text.lower() for f in det.iter_filth(text)]
    assert "point.com" not in urls


def test_sharepoint_url_detector_cleanup_and_yield() -> None:
    """SharePointUrlDetector trims whitespace and trailing punctuation and yields."""
    det = SharePointUrlDetector()
    text = (
        "here is https://tenant.sharepoint.com/sites/x/Lists/y (), and another "
        "https://contoso.sharepoint.com/sites/a/b/c?x=1,"
    )
    items = list(det.iter_filth(text))
    assert any("sharepoint.com/sites/x/Lists/y".lower() in f.text.lower() for f in items)
    assert any("contoso.sharepoint.com/sites/a/b/c?x=1" in f.text for f in items)


def test_ip_detectors_private_and_public() -> None:
    """Private and public IP detectors yield expected matches."""
    priv = PrivateIPDetector()
    pub = PublicIPDetector()
    # Cover verbose echo branches
    priv._verbose = True  # type: ignore[attr-defined]
    pub._verbose = True  # type: ignore[attr-defined]
    text = "see 192.168.1.1 and 10.0.10.5 and 172.20.1.2; public 8.8.8.8 and 9.9.9.9"
    priv_out = {f.text for f in priv.iter_filth(text)}
    pub_out = {f.text for f in pub.iter_filth(text)}
    assert {"192.168.1.1", "10.0.10.5", "172.20.1.2"}.issubset(priv_out)
    assert {"8.8.8.8", "9.9.9.9"}.issubset(pub_out)
