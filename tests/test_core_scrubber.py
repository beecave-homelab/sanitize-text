"""Tests for sanitize_text.core.scrubber.

Covers:
- Detector description helpers (including spaCy-enabled toggle).
- setup_scrubber selection, verbose propagation, and custom detector.
- scrub_text success/error aggregation.
- collect_filth replacement application.
"""

import sys
from types import ModuleType

import pytest


@pytest.fixture()
def stub_scrubadub(monkeypatch):
    """Provide a minimal 'scrubadub' package stub for tests.

    Includes:
    - post_processors.PostProcessor base class
    - filth submodule placeholder
    - Scrubber class with clean/iter_filth hooks

    Returns:
        ModuleType: The stubbed root ``scrubadub`` package.
    """
    pkg = ModuleType("scrubadub")

    post_processors = ModuleType("scrubadub.post_processors")

    class PostProcessor:  # noqa: D401 - simple stub
        """Stub base class."""

    post_processors.PostProcessor = PostProcessor

    filth = ModuleType("scrubadub.filth")

    class FakeFilth:  # minimal shape used by replacer
        def __init__(self, type_: str, text: str):
            self.type = type_
            self.text = text
            self.replacement_string = None

    filth.Filth = FakeFilth

    class Scrubber:
        def __init__(self, *, locale: str, detector_list: list, post_processor_list: list):
            self.locale = locale
            self.detector_list = detector_list
            self.post_processor_list = post_processor_list
            self.detectors = {}
            self._clean_calls = 0

        def clean(self, text: str) -> str:
            self._clean_calls += 1
            # return deterministic marker to validate propagation
            return f"[{self.locale}:{len(self.detector_list)}]{text}"

        def iter_filth(self, text: str):
            # deterministic single item
            return [filth.Filth("name", "John Doe")]

    pkg.post_processors = post_processors
    pkg.filth = filth
    pkg.Scrubber = Scrubber

    monkeypatch.setitem(sys.modules, "scrubadub", pkg)
    monkeypatch.setitem(sys.modules, "scrubadub.post_processors", post_processors)
    monkeypatch.setitem(sys.modules, "scrubadub.filth", filth)

    return pkg


@pytest.fixture()
def stub_custom_detectors(monkeypatch):
    """Stub out custom detector modules used during setup_scrubber.

    - CustomWordDetector used when custom_text is provided
    - DutchEntityDetector with cache cleared for nl_NL

    Returns:
        tuple[ModuleType, ModuleType]: The custom_detectors and base modules.
    """
    mod = ModuleType("sanitize_text.utils.custom_detectors")

    class CustomWordDetector:
        def __init__(self, *, custom_text: str):
            self.name = "custom_word"
            self.custom_text = custom_text
            self._verbose = False

    mod.CustomWordDetector = CustomWordDetector

    base = ModuleType("sanitize_text.utils.custom_detectors.base")

    class DutchEntityDetector:  # only the cache and reset hook are accessed
        _dutch_loaded_entities = {"seed"}

        @classmethod
        def reset_loaded_entities(cls) -> None:
            cls._dutch_loaded_entities.clear()

    base.DutchEntityDetector = DutchEntityDetector

    monkeypatch.setitem(sys.modules, "sanitize_text.utils.custom_detectors", mod)
    monkeypatch.setitem(sys.modules, "sanitize_text.utils.custom_detectors.base", base)

    return mod, base


class FakeDetector:
    """Minimal detector stub with ``name`` and ``_verbose`` attributes."""

    def __init__(self, name: str):
        """Initialize with a detector ``name``.

        Args:
            name: Detector identifier.
        """
        self.name = name
        self._verbose = False


@pytest.fixture()
def patch_minimal_specs(monkeypatch):
    """Replace detector specs with minimal, import-free factories for tests."""
    from sanitize_text.core import scrubber as s

    def f_alpha(_):
        return FakeDetector("alpha")

    def f_beta(_):
        return FakeDetector("beta")

    def f_gamma(_):
        return FakeDetector("gamma")

    alpha = s.DetectorSpec(name="alpha", description="Alpha", factory=f_alpha)
    beta = s.DetectorSpec(name="beta", description="Beta", factory=f_beta)
    gamma = s.DetectorSpec(name="gamma", description="Gamma", factory=f_gamma)

    monkeypatch.setattr(s, "GENERIC_DETECTORS", [alpha], raising=True)
    monkeypatch.setattr(s, "LOCALE_DETECTORS", {"en_US": [beta], "nl_NL": [gamma]}, raising=True)


def test_get_locale_detector_descriptions_spacy_toggle(monkeypatch):
    """spacy_entities is conditionally present based on availability toggle."""
    from sanitize_text.core import scrubber as s

    # When spaCy unavailable, spacy_entities should be filtered out
    monkeypatch.setattr(s, "_spacy_is_available", lambda: False, raising=True)
    en_desc = s.get_locale_detector_descriptions("en_US")
    assert ("spacy_entities" in en_desc) is False

    # When spaCy available, spacy_entities is enabled
    monkeypatch.setattr(s, "_spacy_is_available", lambda: True, raising=True)
    en_desc2 = s.get_locale_detector_descriptions("en_US")
    assert "spacy_entities" in en_desc2


def test_setup_scrubber_selection_verbose_and_custom(
    stub_scrubadub, stub_custom_detectors, patch_minimal_specs, caplog
):
    """Validate selection filtering, verbose propagation, and custom detector."""
    from sanitize_text.core import scrubber as s

    # Include an invalid detector in selection to trigger warning
    caplog.set_level("WARNING")
    scrub = s.setup_scrubber(
        locale="nl_NL",
        selected_detectors=["alpha", "invalid"],
        custom_text="XYZ",
        verbose=True,
    )

    # Dutch cache cleared
    from sanitize_text.utils.custom_detectors.base import DutchEntityDetector

    assert DutchEntityDetector._dutch_loaded_entities == set()

    # Verbose propagated to scrubber and detectors
    assert getattr(scrub, "_verbose", False) is True
    for det in scrub.detector_list:
        assert getattr(det, "_verbose", False) is True

    # Custom detector present and detectors reduced to valid ones
    names = list(scrub.detectors.keys())
    assert "custom_word" in names
    assert "alpha" in names
    assert "invalid" not in names

    # Warning logged for invalid detector
    assert any("Invalid detector(s)" in r.message for r in caplog.records)


def test_scrub_text_success_and_errors(monkeypatch):
    """scrub_text returns default locale output and raises when it fails."""
    from sanitize_text.core import scrubber as s

    class FakeScrubber:
        def __init__(self, *, locale: str, detector_list=None, post_processor_list=None):
            self.locale = locale
            self.detector_list = detector_list or []
            self.detectors = {d.name: d for d in self.detector_list} or {"d": object()}

        def clean(self, text: str) -> str:
            return f"{text}|{self.locale}"

    def setup(locale, selected_detectors, custom_text, verbose=False):  # noqa: ARG001 - signature match
        if locale == s.DEFAULT_LOCALE:
            return FakeScrubber(locale=locale)
        raise AssertionError("unexpected locale in test")

    monkeypatch.setattr(s, "setup_scrubber", setup, raising=True)

    outcome = s.scrub_text("hello")
    assert outcome.texts == {s.DEFAULT_LOCALE: f"hello|{s.DEFAULT_LOCALE}"}
    assert not outcome.errors
    assert outcome.detectors[s.DEFAULT_LOCALE] == ["d"]

    # Failure for requested locale raises
    def setup_all_fail(locale, *_args, **_kwargs):
        raise RuntimeError(f"fail-{locale}")

    monkeypatch.setattr(s, "setup_scrubber", setup_all_fail, raising=True)
    with pytest.raises(Exception, match="All processing attempts failed"):
        s.scrub_text("hello", locale="en_US")


def test_collect_filth_applies_replacer(monkeypatch, stub_scrubadub):
    """collect_filth returns filths with replacement strings applied for default locale."""
    from sanitize_text.core import scrubber as s

    class FakeFilth:
        def __init__(self, type_: str, text: str):
            self.type = type_
            self.text = text
            self.replacement_string = None

    class FakeScrubber:
        def __init__(self, *, locale: str, detector_list=None, post_processor_list=None):
            self.locale = locale

        def iter_filth(self, text: str):  # noqa: ARG002
            return [FakeFilth("name", "John"), FakeFilth("markdown_url", "http://x")]  # URL-like

    monkeypatch.setattr(
        s,
        "setup_scrubber",
        lambda loc, *_a, **_k: FakeScrubber(locale=loc),
        raising=True,
    )

    # Ensure import of scrubadub.filth in collect_filth passes
    sf = ModuleType("scrubadub.filth")
    monkeypatch.setitem(sys.modules, "scrubadub.filth", sf)

    out = s.collect_filth("hello")
    assert set(out.keys()) == {s.DEFAULT_LOCALE}

    # Each filth should have replacement_string assigned
    for locale, filths in out.items():
        assert all(getattr(f, "replacement_string", None) for f in filths), locale
        # Check placeholder style heuristics
        assert any(f.replacement_string.startswith("NAME-") for f in filths)
        assert any(f.replacement_string.startswith("URL-") for f in filths)


def test_get_generic_detector_descriptions_defaults(patch_minimal_specs):
    """Generic detector descriptions default to nl_NL when locale omitted."""
    from sanitize_text.core import scrubber as s

    out_default = s.get_generic_detector_descriptions()
    out_en = s.get_generic_detector_descriptions("en_US")

    assert out_default == {"alpha": "Alpha"}
    assert out_en == {"alpha": "Alpha"}


def test_get_available_detectors_all_and_specific(patch_minimal_specs):
    """get_available_detectors returns all locales or a specific combined mapping."""
    from sanitize_text.core import scrubber as s

    all_out = s.get_available_detectors()
    assert set(all_out.keys()) == {"en_US", "nl_NL"}
    assert all_out["en_US"] == {"beta": "Beta"}
    assert all_out["nl_NL"] == {"gamma": "Gamma"}

    one = s.get_available_detectors("en_US")
    assert one == {"alpha": "Alpha", "beta": "Beta"}


def test_setup_scrubber_defaults_no_custom(
    stub_scrubadub, stub_custom_detectors, patch_minimal_specs
):
    """Default selection builds enabled detectors when none are explicitly selected."""
    from sanitize_text.core import scrubber as s

    scrub = s.setup_scrubber(locale="en_US")
    names = set(scrub.detectors.keys())
    assert names == {"alpha", "beta"}


def test_build_spacy_detector_with_stub(monkeypatch):
    """_build_spacy_detector can construct using a stubbed spaCy module."""
    import sys
    from types import ModuleType

    from sanitize_text.core import scrubber as s

    mod = ModuleType("scrubadub_spacy.detectors")

    class SpacyEntityDetector:  # noqa: D401 - simple stub
        """Stub detector capturing init args for assertions."""

        def __init__(self, *, model: str, name: str):
            self.model = model
            self.name = name

    mod.SpacyEntityDetector = SpacyEntityDetector
    monkeypatch.setitem(sys.modules, "scrubadub_spacy.detectors", mod)

    ctx = s.DetectorContext(locale="en_US")
    det = s._build_spacy_detector(ctx)
    assert isinstance(det, SpacyEntityDetector)
    assert det.model == "en_core_web_sm"
    assert det.name == "spacy_en"

    # Also cover the _spacy_enabled predicate
    monkeypatch.setattr(s, "_spacy_is_available", lambda: True, raising=True)
    assert s._spacy_enabled(ctx) is True
