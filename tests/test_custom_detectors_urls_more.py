"""Additional URL detector tests to cover heuristics and verbose branches."""

from __future__ import annotations

import pytest

from sanitize_text.utils.custom_detectors.markdown_url_detector import MarkdownUrlDetector
from sanitize_text.utils.custom_detectors.sharepoint_url_detector import SharePointUrlDetector
from sanitize_text.utils.custom_detectors.url_detector import BareDomainDetector


def test_bare_domain_detector_mixed_case_bare_is_skipped() -> None:
    """Mixed-case bare domain without protocol/www is skipped by heuristic."""
    det = BareDomainDetector()
    text = "This should skip Mixed.Case.Domain.com but accept www.Mixed.com and http://Foo.dev"
    urls = [f.text for f in det.iter_filth(text)]
    assert any("www.Mixed.com".lower() in u.lower() for u in urls)
    assert any("foo.dev" in u.lower() for u in urls)
    assert not any("Mixed.Case.Domain.com".lower() == u.lower() for u in urls)


def test_bare_domain_detector_sharepoint_prev_next_combinations() -> None:
    """Skip epoint.com/harepoint.com/point.com when doc references sharepoint near fragments."""
    det = BareDomainDetector()
    # Prev combined: 'share' + 'epoint.com'
    text1 = "... share epoint.com ..."
    # Next combined: 'hare' + 'point.com'
    text2 = "... harepoint.com ..."  # host itself is harepoint.com
    # Larger-window and doc-level checks
    text3 = (
        "prefix point.com suffix with lots of text mentioning sharepoint somewhere in the document."
    )
    all_text = "\n".join([text1, text2, text3])
    urls = [f.text.lower() for f in det.iter_filth(all_text)]
    assert "epoint.com" not in urls
    assert "harepoint.com" not in urls
    assert "point.com" not in urls


def test_markdown_url_detector_verbose_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Verbose mode prints per-match lines and totals (covering echo branches)."""
    det = MarkdownUrlDetector()
    det._verbose = True  # type: ignore[attr-defined]
    text = "See [a](http://example.com) and [[b]](https://x.y)"
    _ = list(det.iter_filth(text))
    out = capsys.readouterr().out
    assert "Scanning for Markdown URLs" in out
    assert "Total matches" in out


def test_sharepoint_url_detector_verbose_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Verbose mode prints per-match lines and totals for sharepoint detector."""
    det = SharePointUrlDetector()
    det._verbose = True  # type: ignore[attr-defined]
    text = "https://t.sharepoint.com/sites/a/b/c and https://x.sharepoint.com/d/e/f?g=1"
    _ = list(det.iter_filth(text))
    out = capsys.readouterr().out
    assert "Scanning for SharePoint URLs" in out
    assert "Total matches" in out
