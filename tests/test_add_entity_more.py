"""Additional tests for add_entity.main to cover error branches and CLI options."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from sanitize_text.add_entity import main as exported_main
from sanitize_text.add_entity.main import EntityManager


def test_load_json_jsondecodeerror(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid JSON triggers JSONDecodeError branch and returns empty list."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json}", encoding="utf-8")

    mgr = EntityManager()
    out = mgr.load_json(bad)
    assert out == []
    err = capsys.readouterr().err
    assert "Invalid JSON format" in err


def test_cli_main_with_all_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """Click CLI handles -c/-n/-o and invokes EntityManager.add_entity accordingly."""
    calls: list[tuple[str, str]] = []

    def fake_add(self: EntityManager, et: str, val: str) -> bool:  # noqa: D401 - test stub
        calls.append((et, val))
        return True

    monkeypatch.setattr(EntityManager, "add_entity", fake_add, raising=True)

    runner = click.testing.CliRunner()
    res = runner.invoke(exported_main, ["-c", "CityX", "-n", "NameY", "-o", "OrgZ"])  # type: ignore[arg-type]
    assert res.exit_code == 0

    assert ("city", "CityX") in calls
    assert ("name", "NameY") in calls
    assert ("organization", "OrgZ") in calls
