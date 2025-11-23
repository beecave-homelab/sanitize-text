"""Tests for :mod:`sanitize_text.cli.main` CLI behavior and helpers."""

from __future__ import annotations

import importlib
from typing import Any

from click import command, echo
from click.testing import CliRunner


def test_list_detectors_flag_prints_catalog(monkeypatch) -> None:
    """--list-detectors should print generic and per-locale detectors then exit."""
    mod = importlib.import_module("sanitize_text.cli.main")

    monkeypatch.setattr(mod, "get_generic_detector_descriptions", lambda: {"email": "Email"})
    monkeypatch.setattr(mod, "get_available_detectors", lambda: {"en_US": {"name": "Name"}})

    runner = CliRunner()
    result = runner.invoke(mod.main, ["--list-detectors"])

    assert result.exit_code == 0
    assert "Available detectors:" in result.output
    assert "Generic detectors" in result.output
    assert "Locale-specific detectors" in result.output


def test_main_prints_to_stdout_when_text_and_no_output(monkeypatch) -> None:
    """When -t is used with no -o/--output-format, print scrubbed text to stdout."""
    mod = importlib.import_module("sanitize_text.cli.main")

    # Avoid spinner side-effects
    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)

    # Ensure input resolution returns our text (even if provided)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")
    # Return scrubbed payload
    monkeypatch.setattr(mod, "_run_scrub", lambda **k: "SCRUB")

    runner = CliRunner()
    result = runner.invoke(mod.main, ["-t", "foo"])

    assert result.exit_code == 0
    assert result.output.strip().endswith("SCRUB")


def test_main_writes_to_output_when_path_given(monkeypatch, tmp_path) -> None:
    """When -o is provided, it should write via write_output and print the path."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")
    monkeypatch.setattr(mod, "_run_scrub", lambda **k: "SCRUB")

    calls: dict[str, Any] = {}

    def fake_write_output(**kwargs: Any) -> str:  # noqa: ANN401 - test shim
        calls.update(kwargs)
        return str(tmp_path / "out.txt")

    monkeypatch.setattr(mod, "write_output", fake_write_output)

    runner = CliRunner()
    target = tmp_path / "out.txt"
    result = runner.invoke(mod.main, ["-t", "foo", "-o", str(target)])

    assert result.exit_code == 0
    assert "Scrubbed text saved to" in result.output
    assert calls.get("text") == "SCRUB"


def test_main_download_models_called_when_flag(monkeypatch) -> None:
    """--download-nlp-models should invoke download_optional_models before processing."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")
    monkeypatch.setattr(mod, "_run_scrub", lambda **k: "SCRUB")

    calls = {"dl": 0}

    def _dl() -> None:
        calls["dl"] = calls["dl"] + 1

    monkeypatch.setattr(mod, "download_optional_models", _dl)

    runner = CliRunner()
    result = runner.invoke(mod.main, ["-t", "foo", "--download-nlp-models"])

    assert result.exit_code == 0
    assert calls["dl"] == 1


def test_run_scrub_basic_non_verbose(monkeypatch) -> None:
    """_run_scrub formats results per-locale and warns for failed locales."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyOutcome:
        def __init__(self) -> None:
            self.texts = {"en_US": "EN", "nl_NL": "NL"}
            self.errors = {}
            self.detectors = {"en_US": ["email"]}

    monkeypatch.setattr(mod, "scrub_text", lambda *a, **k: DummyOutcome())
    monkeypatch.setattr(mod, "maybe_cleanup", lambda text, enabled: text)

    out = mod._run_scrub(
        input_text="x",
        locale=None,
        detectors=None,
        custom=None,
        cleanup=True,
        verbose=False,
    )
    # When no locale is specified, nl_NL should be the default output without headers.
    assert out == "NL"


def test_run_scrub_verbose_logs_and_collects(monkeypatch) -> None:
    """Verbose mode emits progress and collects filth for locales."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyOutcome:
        def __init__(self) -> None:
            self.texts = {"en_US": "EN"}
            self.errors = {}
            self.detectors = {"en_US": ["email", "url"]}

    monkeypatch.setattr(mod, "scrub_text", lambda *a, **k: DummyOutcome())
    monkeypatch.setattr(mod, "maybe_cleanup", lambda text, enabled: text)
    monkeypatch.setattr(
        importlib.import_module("sanitize_text.core.scrubber"),
        "collect_filth",
        lambda *a, **k: {"en_US": []},
    )

    # Capture output via CliRunner by invoking a tiny wrapper command
    # to run _run_scrub in verbose mode and echo result.
    @command()
    def _runner_cmd() -> None:
        text = mod._run_scrub(
            input_text="x",
            locale=None,
            detectors=None,
            custom=None,
            cleanup=True,
            verbose=True,
        )
        echo(text)

    runner = CliRunner()
    result = runner.invoke(_runner_cmd)

    assert result.exit_code == 0
    assert "[Processing locale: en_US]" in result.output
    assert "EN" in result.output
    assert "Results for en_US:" not in result.output


def test_main_error_from_read_input_source(monkeypatch) -> None:
    """Errors during input resolution should exit with code 1 and show message."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)

    def _raise_read(**_k: Any) -> str:  # noqa: D401 - test shim
        raise Exception("bad")

    monkeypatch.setattr(mod, "read_input_source", _raise_read)

    runner = CliRunner()
    result = runner.invoke(mod.main, ["-t", "foo"])

    assert result.exit_code == 1
    assert "Error: bad" in result.output


def test_main_error_from_run_scrub(monkeypatch) -> None:
    """Errors during _run_scrub should exit 1 and spinner.fail should be safe."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

        def fail(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")

    def _raise_run(**_k: Any) -> str:  # noqa: D401 - test shim
        raise Exception("boom")

    monkeypatch.setattr(mod, "_run_scrub", _raise_run)

    runner = CliRunner()
    result = runner.invoke(mod.main, ["-t", "foo"])

    assert result.exit_code == 1
    assert "Error: boom" in result.output


def test_main_respects_output_format_option(monkeypatch, tmp_path) -> None:
    """--output-format should be honored even without -o path."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")
    monkeypatch.setattr(mod, "_run_scrub", lambda **k: "SCRUB")

    out_dir = tmp_path

    def fake_write_output(**kwargs: Any) -> str:  # noqa: ANN401 - test shim
        # Ensure format value propagated
        assert kwargs.get("fmt") == "pdf"
        return str(out_dir / "scrubbed.pdf")

    monkeypatch.setattr(mod, "write_output", fake_write_output)

    runner = CliRunner()
    result = runner.invoke(mod.main, ["-t", "foo", "--output-format", "pdf"])

    assert result.exit_code == 0
    assert "Scrubbed text saved to" in result.output


def test_main_passes_cli_options_to_run_scrub(monkeypatch) -> None:
    """locale/detectors/custom/cleanup/verbose values propagate to _run_scrub."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    seen: dict[str, Any] = {}

    def _capture(**k: Any) -> str:  # noqa: ANN401 - test shim
        seen.update(k)
        return "SCRUB"

    monkeypatch.setattr(mod, "Halo", DummyHalo)
    monkeypatch.setattr(mod, "read_input_source", lambda **k: "foo")
    monkeypatch.setattr(mod, "_run_scrub", _capture)

    runner = CliRunner()
    result = runner.invoke(
        mod.main,
        [
            "-t",
            "foo",
            "-l",
            "en_US",
            "-d",
            "email url",
            "-c",
            "ACME",
            "--no-cleanup",
            "-v",
        ],
    )

    assert result.exit_code == 0
    assert seen["locale"] == "en_US"
    assert seen["detectors"] == "email url"
    assert seen["custom"] == "ACME"
    assert seen["cleanup"] is False
    assert seen["verbose"] is True


def test_main_passes_pdf_backend_to_read_input_source(monkeypatch, tmp_path) -> None:
    """--pdf-backend should propagate to read_input_source (default and explicit)."""
    mod = importlib.import_module("sanitize_text.cli.main")

    class DummyHalo:
        def __init__(self, *a: Any, **k: Any) -> None:  # noqa: D401
            pass

        def start(self) -> None:  # noqa: D401
            return None

        def succeed(self, *_: Any, **__: Any) -> None:  # noqa: D401
            return None

    monkeypatch.setattr(mod, "Halo", DummyHalo)

    seen: dict[str, Any] = {}

    def fake_read_input_source(**k: Any) -> str:  # noqa: ANN401 - test shim
        seen.update(k)
        return "PDF TEXT"

    monkeypatch.setattr(mod, "read_input_source", fake_read_input_source)
    monkeypatch.setattr(mod, "_run_scrub", lambda **k: "SCRUB")
    monkeypatch.setattr(mod, "write_output", lambda **k: str(tmp_path / "out.txt"))

    runner = CliRunner()

    # Use a real temporary PDF path so Click's Path(exists=True) validation passes.
    pdf_path = tmp_path / "in.pdf"
    pdf_path.write_text("dummy", encoding="utf-8")

    # Default backend
    result = runner.invoke(mod.main, ["-i", str(pdf_path), "-o", str(tmp_path / "a.txt")])
    assert result.exit_code == 0
    assert seen["pdf_backend"] == "pymupdf4llm"

    # Explicit backend
    seen.clear()
    result = runner.invoke(
        mod.main,
        [
            "-i",
            str(pdf_path),
            "-o",
            str(tmp_path / "b.txt"),
            "--pdf-backend",
            "markitdown",
        ],
    )
    assert result.exit_code == 0
    assert seen["pdf_backend"] == "markitdown"
