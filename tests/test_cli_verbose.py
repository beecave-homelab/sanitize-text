"""CLI verbose flag should list found PII replacements."""

from __future__ import annotations

from click.testing import CliRunner

from sanitize_text.cli.main import main


def test_verbose_outputs_mapping() -> None:
    """Running with -v prints mapping of original to replacement."""
    runner = CliRunner()
    text = "Check this site https://example.com for info."
    result = runner.invoke(main, ["-t", text, "-d", "url", "-v"])
    assert result.exit_code == 0
    # mapping line example: url: 'https://example.com' -> 'URL-001'
    assert "->" in result.output
    assert "https://example.com" in result.output
    assert "URL-" in result.output
