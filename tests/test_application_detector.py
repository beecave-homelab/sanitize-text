"""Tests for DutchApplicationDetector and ApplicationFilth."""

from __future__ import annotations

import json
from pathlib import Path

from sanitize_text.core.scrubber import setup_scrubber
from sanitize_text.utils.custom_detectors.base import DutchEntityDetector
from sanitize_text.utils.custom_detectors.dutch_detectors import DutchApplicationDetector
from sanitize_text.utils.filth import ApplicationFilth


def test_dutch_application_detector_empty_file() -> None:
    """DutchApplicationDetector loads successfully with empty applications.json."""
    DutchEntityDetector.reset_loaded_entities()
    det = DutchApplicationDetector()
    assert det.name == "application"
    assert det.filth_cls is ApplicationFilth
    # Empty file means no entities
    assert det.entities == []


def test_application_filth_type() -> None:
    """ApplicationFilth has the correct type."""
    assert ApplicationFilth.type == "application"


def test_dutch_application_detector_matches(tmp_path: Path) -> None:
    """DutchApplicationDetector matches application names from JSON file."""
    DutchEntityDetector.reset_loaded_entities()

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


def test_application_detector_registered_with_scrubadub() -> None:
    """DutchApplicationDetector is registered with scrubadub detector catalog."""
    import scrubadub

    # The detector should be available via scrubadub's registry
    detector_names = scrubadub.detectors.detector_catalogue.get_all()
    assert "application" in detector_names


def test_application_detector_via_setup_scrubber() -> None:
    """Application detector is available via setup_scrubber for nl_NL locale."""
    DutchEntityDetector.reset_loaded_entities()
    scrubber = setup_scrubber(locale="nl_NL")
    assert "application" in scrubber.detectors
    det = scrubber.detectors["application"]
    assert isinstance(det, DutchApplicationDetector)


def test_application_detector_case_insensitive() -> None:
    """Application detector matches regardless of case."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_apps_case.json"
    test_file.write_text(
        json.dumps([{"match": "MyApplication", "filth_type": "application"}]),
        encoding="utf-8",
    )

    class TestDetector(DutchApplicationDetector):
        json_file = "test_apps_case.json"

    det = TestDetector()

    try:
        # Should match all case variants
        for variant in ["MyApplication", "myapplication", "MYAPPLICATION"]:
            matches = list(det.iter_filth(f"Using {variant} today."))
            assert len(matches) == 1, f"Failed to match {variant}"
            assert matches[0].text == variant
    finally:
        test_file.unlink(missing_ok=True)


def test_application_detector_word_boundaries() -> None:
    """Application detector respects word boundaries."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_apps_bounds.json"
    test_file.write_text(
        json.dumps([{"match": "App", "filth_type": "application"}]),
        encoding="utf-8",
    )

    class TestDetector(DutchApplicationDetector):
        json_file = "test_apps_bounds.json"

    det = TestDetector()

    try:
        # Short entity (<=3 chars) requires capitalization
        matches = list(det.iter_filth("Use App today."))
        assert len(matches) == 1
        assert matches[0].text == "App"

        # Lowercase short entity should not match
        matches = list(det.iter_filth("Use app today."))
        assert len(matches) == 0

        # Inside word should not match
        matches = list(det.iter_filth("Use Application today."))
        assert len(matches) == 0
    finally:
        test_file.unlink(missing_ok=True)


def test_application_detector_multiple_matches() -> None:
    """Application detector finds multiple occurrences."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_apps_multi.json"
    test_file.write_text(
        json.dumps([
            {"match": "Salesforce", "filth_type": "application"},
            {"match": "AFAS", "filth_type": "application"},
        ]),
        encoding="utf-8",
    )

    class TestDetector(DutchApplicationDetector):
        json_file = "test_apps_multi.json"

    det = TestDetector()

    try:
        text = "We use Salesforce and AFAS for CRM."
        matches = list(det.iter_filth(text))
        assert len(matches) == 2
        texts = {m.text for m in matches}
        assert texts == {"Salesforce", "AFAS"}
    finally:
        test_file.unlink(missing_ok=True)


def test_application_detector_url_context_filtered() -> None:
    """Application detector does not match inside URLs."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_apps_url.json"
    test_file.write_text(
        json.dumps([{"match": "AppName", "filth_type": "application"}]),
        encoding="utf-8",
    )

    class TestDetector(DutchApplicationDetector):
        json_file = "test_apps_url.json"

    det = TestDetector()

    try:
        # Inside URL should be filtered
        text = "Visit https://example.com/AppName/page for info."
        matches = list(det.iter_filth(text))
        assert len(matches) == 0

        # Outside URL should match
        text = "The AppName system is great."
        matches = list(det.iter_filth(text))
        assert len(matches) == 1
        assert matches[0].text == "AppName"
    finally:
        test_file.unlink(missing_ok=True)


def test_application_detector_deduplication_priority() -> None:
    """Application detector respects Dutch entity deduplication priority."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"

    # Create a location entity
    loc_file = data_dir / "test_apps_loc.json"
    loc_file.write_text(
        json.dumps([{"match": "CRM", "filth_type": "location"}]),
        encoding="utf-8",
    )

    # Create an application entity with same name
    app_file = data_dir / "test_apps_app.json"
    app_file.write_text(
        json.dumps([{"match": "CRM", "filth_type": "application"}]),
        encoding="utf-8",
    )

    class TestLocDetector(DutchEntityDetector):
        name = "location"
        filth_cls = ApplicationFilth  # using same filth class for simplicity
        json_file = "test_apps_loc.json"

    class TestAppDetector(DutchApplicationDetector):
        json_file = "test_apps_app.json"

    try:
        # Load location first (higher priority)
        loc_det = TestLocDetector()
        assert "CRM" in loc_det.entities

        # Application detector should have CRM filtered out
        app_det = TestAppDetector()
        assert "CRM" not in app_det.entities
        assert "crm" not in {e.lower() for e in app_det.entities}
    finally:
        loc_file.unlink(missing_ok=True)
        app_file.unlink(missing_ok=True)


def test_application_detector_verbose_mode() -> None:
    """Application detector respects verbose flag."""
    DutchEntityDetector.reset_loaded_entities()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    test_file = data_dir / "test_apps_verbose.json"
    test_file.write_text(
        json.dumps([{"match": "TestSystem", "filth_type": "application"}]),
        encoding="utf-8",
    )

    class TestDetector(DutchApplicationDetector):
        json_file = "test_apps_verbose.json"

    det = TestDetector()
    det._verbose = True

    try:
        text = "Using TestSystem for testing."
        matches = list(det.iter_filth(text))
        assert len(matches) == 1
        assert matches[0].text == "TestSystem"
    finally:
        test_file.unlink(missing_ok=True)
