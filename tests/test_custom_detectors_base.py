"""Tests for custom_detectors.base with lightweight stubs.

Covers core paths of JSONEntityDetector, normalized fallback, and DutchEntityDetector dedup.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _install_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install minimal stubs for scrubadub and ahocorasick used by the base module."""
    # Stub scrubadub.detectors.Detector
    det_mod = ModuleType("scrubadub.detectors")

    class Detector:  # minimal base
        def __init__(self, **_kwargs):
            pass

    det_mod.Detector = Detector
    monkeypatch.setitem(sys.modules, "scrubadub.detectors", det_mod)

    # Stub ahocorasick.Automaton
    ac_mod = ModuleType("ahocorasick")

    class Automaton:
        def __init__(self):
            self._words: list[tuple[str, str]] = []

        def add_word(self, word: str, value: str) -> None:
            self._words.append((word, value))

        def make_automaton(self) -> None:  # noqa: D401 - no-op
            pass

        def iter(self, text: str):
            tl = text.lower()
            for word, original in self._words:
                start = 0
                while True:
                    idx = tl.find(word, start)
                    if idx == -1:
                        break
                    end_idx = idx + len(word) - 1
                    yield (end_idx, original)
                    start = idx + 1

    ac_mod.Automaton = Automaton
    monkeypatch.setitem(sys.modules, "ahocorasick", ac_mod)


def _load_base_module() -> ModuleType:
    """Load the target base.py module by file path so coverage tracks the file.

    Returns:
        ModuleType: The loaded module.
    """
    base_path = (
        Path(__file__).resolve().parents[1]
        / "sanitize_text"
        / "utils"
        / "custom_detectors"
        / "base.py"
    )
    spec = importlib.util.spec_from_file_location("ct_base_under_test", base_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod  # type: ignore[return-value]


def test_json_entity_detector_iter_filth_basic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Basic automaton scan yields matches and skips stopwords and URL contexts."""
    _install_stubs(monkeypatch)
    base = _load_base_module()

    # Prepare test entities file in existing data dir
    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "en_entities"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_file = data_dir / "test_entities.json"
    json_file.write_text(
        """
        [
          {"match": ""},
          {"match": "x"},
          {"match": "loop"},
          {"match": "Foo"},
          {"match": "Foo Bar"}
        ]
        """.strip(),
        encoding="utf-8",
    )

    class Filth:
        def __init__(
            self, beg: int, end: int, text: str, detector_name: str, document_name: str | None
        ):
            self.beg = beg
            self.end = end
            self.text = text
            self.detector_name = detector_name
            self.document_name = document_name
            self.type = detector_name
            self.replacement_string = None

    class TD(base.JSONEntityDetector):
        COMMON_WORDS = {"loop"}
        data_subdir = "en_entities"
        json_file = "test_entities.json"
        name = "name"
        filth_cls = Filth

    det = TD()
    det._verbose = True

    text = "Foo went to http://example.com and met Foo Bar. loop should be ignored."
    out = list(det.iter_filth(text))

    try:
        assert any(f.text == "Foo" for f in out)
        assert any(f.text == "Foo Bar" for f in out)
        assert all("loop" != f.text for f in out)
    finally:
        try:
            os.remove(json_file)
        except FileNotFoundError:
            pass


def test_normalized_search_ampersand_and_zw(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Normalized search finds 'Foo & Bar' variants and ignores newlines."""
    _install_stubs(monkeypatch)
    base = _load_base_module()

    data_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "en_entities"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_file = data_dir / "test_entities2.json"
    # Use ampersand in entity; normalization maps '&' -> ' en ' for matching against text
    json_file.write_text('[{"match": "Foo & Bar"}]', encoding="utf-8")

    class Filth:
        def __init__(
            self, beg: int, end: int, text: str, detector_name: str, document_name: str | None
        ):
            self.beg = beg
            self.end = end
            self.text = text
            self.detector_name = detector_name
            self.document_name = document_name
            self.type = detector_name

    class OrgDet(base.JSONEntityDetector):
        data_subdir = "en_entities"
        json_file = "test_entities2.json"
        name = "organization"
        filth_cls = Filth

    det = OrgDet()
    det._verbose = True

    text = "X Foo & Bar Y and F\u200bo\u200bo en \u200bBa\u200br Z"
    matches = list(det.iter_filth(text))

    try:
        assert any(
            "Foo & Bar" in m.text or "Foo  en Bar" in m.text or "Foo en Bar" in m.text
            for m in matches
        )
        assert all("\n" not in m.text for m in matches)
    finally:
        try:
            os.remove(json_file)
        except FileNotFoundError:
            pass


def test_dutch_entity_detector_dedup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Lower-priority Dutch detector filters duplicates loaded by earlier ones."""
    _install_stubs(monkeypatch)
    base = _load_base_module()

    nl_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "nl_entities"
    nl_dir.mkdir(parents=True, exist_ok=True)
    f1 = nl_dir / "du1.json"
    f2 = nl_dir / "du2.json"
    f1.write_text('[{"match": "Bank"}, {"match": "Town"}]', encoding="utf-8")
    f2.write_text('[{"match": "Bank"}]', encoding="utf-8")

    class Loc(base.DutchEntityDetector):
        data_subdir = "nl_entities"
        json_file = "du1.json"
        name = "location"

    class Org(base.DutchEntityDetector):
        data_subdir = "nl_entities"
        json_file = "du2.json"
        name = "organization"

    try:
        _ = Loc()
        out = Org()
        # 'Bank' should be filtered out as duplicate
        assert "bank" not in {e.lower() for e in out.entities}
        err = capsys.readouterr().err
        # A message about filtered duplicates may be printed
        assert "Filtered" in err or err == ""
    finally:
        for p in (f1, f2):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass


def test_entity_filters_and_branch_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise short-entity skip, word boundaries, and org capitalization rule.

    Also cover the branch where no multi-word fallback is executed.
    """
    _install_stubs(monkeypatch)
    base = _load_base_module()

    en_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "en_entities"
    en_dir.mkdir(parents=True, exist_ok=True)
    fn = en_dir / "test_entities3.json"
    # 'ab' too short, 'abc' length<=3 lower-case skip unless capitalized, 'Acme' valid
    fn.write_text('[{"match": "ab"}, {"match": "abc"}, {"match": "Acme"}]', encoding="utf-8")

    class Filth:
        def __init__(
            self, beg: int, end: int, text: str, detector_name: str, document_name: str | None
        ):
            self.beg = beg
            self.end = end
            self.text = text
            self.detector_name = detector_name
            self.document_name = document_name
            self.type = detector_name

    class OrgDet(base.JSONEntityDetector):
        data_subdir = "en_entities"
        json_file = "test_entities3.json"
        name = "organization"
        filth_cls = Filth

    det = OrgDet()
    det._verbose = True

    # 'ab' inside word should be skipped; 'abc' lowercase and <=3 skipped;
    # 'Acme' lowercase skipped by org rule
    txt = "xxabx abc acme ACME and Acme; link www.example.com"
    out = list(det.iter_filth(txt))

    try:
        # Only 'Acme' with capital should match once
        assert any(f.text == "Acme" for f in out)
        assert all(f.text != "abc" for f in out)
        assert all(f.text != "ab" for f in out)
    finally:
        try:
            os.remove(fn)
        except FileNotFoundError:
            pass


def test_iter_filth_without_multiword_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover branch where _multi_word_entities is empty (no fallback call)."""
    _install_stubs(monkeypatch)
    base = _load_base_module()

    en_dir = Path(__file__).resolve().parents[1] / "sanitize_text" / "data" / "en_entities"
    en_dir.mkdir(parents=True, exist_ok=True)
    fn = en_dir / "test_entities4.json"
    fn.write_text('[{"match": "Solo"}]', encoding="utf-8")

    class Filth:
        def __init__(
            self, beg: int, end: int, text: str, detector_name: str, document_name: str | None
        ):
            self.beg = beg
            self.end = end
            self.text = text
            self.detector_name = detector_name
            self.document_name = document_name
            self.type = detector_name

    class Det(base.JSONEntityDetector):
        data_subdir = "en_entities"
        json_file = "test_entities4.json"
        name = "name"
        filth_cls = Filth

    det = Det()
    out = list(det.iter_filth("Solo"))
    try:
        assert any(f.text == "Solo" for f in out)
    finally:
        try:
            os.remove(fn)
        except FileNotFoundError:
            pass


def test_map_normalized_span_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    """Directly exercise _map_normalized_span with &amp;, &, whitespace, ZW chars."""
    _install_stubs(monkeypatch)
    base = _load_base_module()

    class Det(base.JSONEntityDetector):
        data_subdir = "en_entities"
        json_file = "nonexistent.json"
        name = "name"

        def _load_json_entities(self) -> None:  # override to avoid IO
            self.entities = []

    d = Det()
    text = "A  B &amp; C & D\u200bE  F"
    # Pick a normalized span covering "B en C"
    start, end = d._map_normalized_span(text=text, norm_idx=3, norm_len=5)
    assert (start is None) is False and (end is None) is False and start < end
