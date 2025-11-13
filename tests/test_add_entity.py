"""Tests for :mod:`sanitize_text.add_entity.main` and entrypoints."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import click
import pytest

from sanitize_text.add_entity.main import EntityManager
from sanitize_text.add_entity.main import main as add_entity_cli


def test_entity_manager_load_and_save_json_success(tmp_path: Path) -> None:
    """load_json returns parsed data and save_json writes content."""
    file_path = tmp_path / "cities.json"
    payload = [{"match": "Amsterdam", "filth_type": "location"}]

    # save_json creates the file
    mgr = EntityManager()
    assert mgr.save_json(file_path, payload) is True

    # load_json reads it back
    data = mgr.load_json(file_path)
    assert data == payload


def test_entity_manager_load_json_not_found(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing file yields [], prints error to stderr."""
    mgr = EntityManager()
    missing = tmp_path / "missing.json"

    result = mgr.load_json(missing)

    assert result == []
    err = capsys.readouterr().err
    assert f"Error: File {missing} not found." in err


def test_entity_manager_save_json_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """PermissionError during write is handled gracefully."""
    mgr = EntityManager()
    target = tmp_path / "blocked.json"

    def fake_open(*args: Any, **kwargs: Any):  # noqa: ANN401 - test shim
        raise PermissionError

    # Only patch builtins.open within this test scope
    monkeypatch.setattr("builtins.open", fake_open)

    ok = mgr.save_json(target, [])
    assert ok is False
    err = capsys.readouterr().err
    assert f"Error: Permission denied when writing to {target}" in err


def test_add_entity_invalid_type(capsys: pytest.CaptureFixture[str]) -> None:
    """Invalid entity type returns False and prints an error."""
    mgr = EntityManager()
    ok = mgr.add_entity("invalid", "X")
    assert ok is False
    err = capsys.readouterr().err
    assert "Error: Invalid entity type" in err


def test_add_entity_duplicate_and_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Duplicate detection prevents add; otherwise adds and sorts then saves."""
    # Prepare temp files for manager
    cities = tmp_path / "cities.json"
    initial = [{"match": "Amsterdam", "filth_type": "location"}]
    cities.write_text(json.dumps(initial), encoding="utf-8")

    mgr = EntityManager()
    mgr.files["city"] = cities

    # Duplicate attempt
    ok_dup = mgr.add_entity("city", "Amsterdam")
    assert ok_dup is False
    assert "already exists" in capsys.readouterr().err

    # Add new entry
    ok_add = mgr.add_entity("city", "Breda")
    assert ok_add is True

    # Verify persisted and sorted
    data = json.loads(cities.read_text(encoding="utf-8"))
    assert [e["match"] for e in data] == ["Amsterdam", "Breda"]


def test_add_entity_save_failure_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """If save_json returns False, add_entity returns False without success message."""
    mgr = EntityManager()
    cities = tmp_path / "cities.json"
    cities.write_text("[]", encoding="utf-8")
    mgr.files["city"] = cities

    # Force save_json failure
    def fail_save(path: Path, data: list[dict[str, str]]) -> bool:  # noqa: ARG001 - parity
        return False

    mgr.save_json = fail_save  # type: ignore[method-assign]

    ok = mgr.add_entity("city", "Zwolle")
    assert ok is False
    out = capsys.readouterr().out
    assert "Successfully added" not in out


def test_add_entity_cli_help_shown_when_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Click CLI prints help when invoked with no options."""
    runner = click.testing.CliRunner()
    result = runner.invoke(add_entity_cli, [])
    assert result.exit_code == 0
    assert "Add new entities to sanitization lists." in result.output


def test_add_entity_dunder_main_invokes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """`python -m sanitize_text.add_entity` invokes main function."""
    calls = {"main": 0}

    def fake_main() -> None:
        calls["main"] += 1

    monkeypatch.setitem(
        sys.modules,
        "sanitize_text.add_entity.main",
        SimpleNamespace(main=fake_main),
    )
    runpy.run_module("sanitize_text.add_entity.__main__", run_name="__main__")
    sys.modules.pop("sanitize_text.add_entity.main", None)

    assert calls["main"] == 1


def test_add_entity_init_reexports_main_identity() -> None:
    """The package-level `main` should re-export the module's `main` symbol."""
    # Import both without invoking the command to avoid parsing pytest args
    from sanitize_text.add_entity import main as exported_main  # type: ignore
    from sanitize_text.add_entity.main import main as module_main  # type: ignore

    assert exported_main is module_main
