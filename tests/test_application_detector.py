"""Tests for DutchApplicationDetector and ApplicationFilth."""

from __future__ import annotations

from sanitize_text.utils.custom_detectors.dutch_detectors import DutchApplicationDetector
from sanitize_text.utils.filth import ApplicationFilth


def test_dutch_application_detector_empty_file() -> None:
    """DutchApplicationDetector loads successfully with empty applications.json."""
    det = DutchApplicationDetector()
    assert det.name == "application"
    assert det.filth_cls is ApplicationFilth
    # Empty file means no entities
    assert det.entities == []


def test_application_filth_type() -> None:
    """ApplicationFilth has the correct type."""
    assert ApplicationFilth.type == "application"


def test_dutch_application_detector_matches(tmp_path: None) -> None:  # noqa: ARG001
    """DutchApplicationDetector matches application names from JSON file."""
    import json
    from pathlib import Path

    # Create a temporary test JSON file
    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_applications.json"
    test_file.write_text(
        json.dumps([{"match": "TestApp", "filth_type": "application"}]),
        encoding="utf-8",
    )

    # Create a test detector using the test file
    class TestAppDetector(DutchApplicationDetector):
        json_file = "test_applications.json"

    det = TestAppDetector()
    text = "I used TestApp yesterday."
    matches = list(det.iter_filth(text))

    try:
        assert len(matches) == 1
        assert matches[0].text == "TestApp"
        assert isinstance(matches[0], ApplicationFilth)
    finally:
        test_file.unlink(missing_ok=True)
