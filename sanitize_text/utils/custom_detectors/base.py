"""Base classes for custom detectors."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

import click
from scrubadub.detectors import Detector


class JSONEntityDetector(Detector):
    """Base class for detectors that load entities from packaged JSON lists."""

    #: Common words that should never be considered entities. Subclasses can
    #: override this with locale-specific stop-word sets.
    COMMON_WORDS: set[str] = set()

    #: Name of the directory inside ``sanitize_text/data`` that contains the
    #: JSON files for this detector family. Subclasses must override it.
    data_subdir: str | None = None

    #: Name of the JSON file to load. Subclasses must override it.
    json_file: str

    def __init__(self, **kwargs: object) -> None:
        """Initialize the detector and load entity data from JSON."""
        super().__init__(**kwargs)
        self.entities: list[str] = []
        self._load_json_entities()
        # Precompile regex patterns for entities to avoid per-call compilation cost
        self._compiled_patterns: list[tuple[str, re.Pattern[str], bool]] = []
        self._prepare_patterns()

    def _load_json_entities(self) -> None:
        """Populate ``self.entities`` with matches from the JSON resource.

        Raises:
            ValueError: If ``data_subdir`` is not specified on the subclass.
        """
        if not self.data_subdir:
            raise ValueError(
                "data_subdir must be defined for JSONEntityDetector subclasses"
            )

        try:
            data_dir = Path(__file__).parent.parent.parent / "data" / self.data_subdir
            filepath = data_dir / self.json_file

            if not filepath.exists():
                click.echo(
                    f"Warning: Could not find entity file {self.json_file}", err=True
                )
                return

            with open(filepath, encoding="utf-8") as file_handle:
                entities = json.load(file_handle)
                for entity in entities:
                    match = entity["match"].strip()
                    # Skip empty strings, single characters, and common words
                    if (
                        len(match) <= 1
                        or match.lower() in self.COMMON_WORDS
                        or not any(char.isalpha() for char in match)
                    ):
                        continue
                    self.entities.append(match)
        except Exception as exc:
            click.echo(
                f"Warning: Could not load JSON entity file {self.json_file}: {exc}",
                err=True,
            )

    def _prepare_patterns(self) -> None:
        """Precompile regex patterns for all entities.

        For multi-word entities, build a whitespace- and zero-width-tolerant
        pattern. For single-token entities, use a simple word-boundary-aware
        pattern. Store the compiled pattern along with the original entity and
        a flag indicating multi-word handling for downstream fallbacks.
        """
        # Unicode-safe boundaries: avoid matching inside alnum+accented sequences
        letters = r"0-9A-Za-zÀ-ÖØ-öø-ÿ"
        for match in self.entities:
            if " " in match:
                tokens = re.split(r"\s+", match.strip())
                alt_tokens: list[str] = []
                zw = r"(?:\u200b|\u200c|\u200d|\u2060|\u00AD)?"

                def _fuzzy_token(tok: str) -> str:
                    parts = [re.escape(ch) + zw for ch in tok]
                    return "".join(parts)

                for t in tokens:
                    if not t:
                        continue
                    if t.lower() == "en":
                        alt_tokens.append(r"(?:" + _fuzzy_token("en") + r"|&|&amp;)")
                    else:
                        alt_tokens.append(_fuzzy_token(t))
                ws = r"(?:\s|\u00A0|\u2007|\u202F)+"
                pattern_text = ws.join(alt_tokens)
            else:
                pattern_text = re.escape(match)
            pattern = rf"(?<![{letters}])" + pattern_text + rf"(?![{letters}])"
            self._compiled_patterns.append((
                match,
                re.compile(pattern, re.IGNORECASE),
                " " in match,
            ))

    def iter_filth(
        self, text: str, document_name: str | None = None
    ) -> Iterator[object]:
        """Yield filth matches for any known entity occurrences in the text."""

        # Helpers for a normalization-aware fallback for multi-word entities
        def _strip_zw(s: str) -> str:
            return re.sub(r"[\u200b\u200c\u200d\u2060\u00AD]", "", s)

        def _collapse_ws(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip()

        def _normalize_for_entity(s: str) -> str:
            s = _strip_zw(s)
            s = re.sub(r"&amp;|&", " en ", s, flags=re.IGNORECASE)
            s = _collapse_ws(s)
            return s.lower()

        for match, compiled, is_multi in self._compiled_patterns:
            matched_any = False
            for found_match in compiled.finditer(text):
                matched_text = found_match.group()
                # Heuristic: skip matches that sit inside a URL-like token or Markdown link
                # Determine token boundaries around the match (till whitespace or brackets)
                l = found_match.start()
                r = found_match.end()
                while l > 0 and not text[l - 1].isspace() and text[l - 1] not in "[]()<>":
                    l -= 1
                tlen = len(text)
                while r < tlen and not text[r].isspace() and text[r] not in "[]()<>":
                    r += 1
                token = text[l:r].lower()
                if (
                    "://" in token
                    or token.startswith("www.")
                    or re.search(r"\.[a-z]{2,15}(?:/|\b)", token)
                ):
                    continue
                # Heuristic: for very short tokens (<=3), require capitalization
                # in the source to avoid matching common words
                # (e.g., Dutch 'hem', 'een').
                if len(match) <= 3 and matched_text.islower():
                    continue
                # Only suppress stopwords when they appear lowercase in text, so
                # proper nouns (capitalized) remain detectable.
                if matched_text.islower() and matched_text in self.COMMON_WORDS:
                    continue
                # For organization/location, require at least one uppercase letter
                # in the matched text to avoid lowercase common-word matches
                if getattr(self, "name", "") in {"organization", "location"} and matched_text.islower():
                    continue
                if not any(char.isalpha() for char in matched_text):
                    continue
                matched_any = True
                yield self.filth_cls(
                    beg=found_match.start(),
                    end=found_match.end(),
                    text=matched_text,
                    detector_name=self.name,
                    document_name=document_name,
                )

            # Normalization-aware fallback for multi-word entities that did not match
            if not matched_any and is_multi:
                norm_text = _normalize_for_entity(text)
                norm_entity = _normalize_for_entity(match)
                pos = 0
                while True:
                    idx = norm_text.find(norm_entity, pos)
                    if idx == -1:
                        break
                    # Map back to original span by walking characters, allowing
                    # zero-widths and flexible whitespace and '&'/'&amp;' vs 'en'.
                    # We scan forward in original text to consume a span that
                    # normalizes to norm_entity.
                    j = 0
                    start = None
                    end = None
                    nlen = len(norm_entity)
                    tlen = len(text)
                    # advance j in original until we reach the start alignment
                    # by skipping chars that vanish during normalization
                    j = 0
                    # Find a starting j such that normalized prefix length matches idx
                    norm_count = 0
                    while j < tlen and norm_count < idx:
                        ch = text[j]
                        if re.match(r"[\u200b\u200c\u200d\u2060\u00AD]", ch):
                            j += 1
                            continue
                        if ch == "&":
                            # Treat &amp; as a unit if present
                            if text[j : j + 5].lower() == "&amp;":
                                norm_count += 3  # ' en'
                                j += 5
                            else:
                                norm_count += 3
                                j += 1
                            continue
                        if ch.isspace():
                            # collapse any run of whitespace to one space
                            while j < tlen and text[j].isspace():
                                j += 1
                            norm_count += 1
                            continue
                        norm_count += 1
                        j += 1

                    start = j
                    # Now consume until we cover nlen normalized chars
                    norm_taken = 0
                    while j < tlen and norm_taken < nlen:
                        ch = text[j]
                        if re.match(r"[\u200b\u200c\u200d\u2060\u00AD]", ch):
                            j += 1
                            continue
                        # Map '&' or '&amp;' to ' en '
                        if text[j : j + 5].lower() == "&amp;":
                            norm_taken += 3
                            j += 5
                            continue
                        if ch == "&":
                            norm_taken += 3
                            j += 1
                            continue
                        if ch.isspace():
                            # collapse any whitespace run
                            while j < tlen and text[j].isspace():
                                j += 1
                            norm_taken += 1
                            continue
                        norm_taken += 1
                        j += 1
                    end = j

                    if start is not None and end is not None and start < end:
                        original_slice = text[start:end]
                        if any(char.isalpha() for char in original_slice):
                            # Skip URLs/Markdown link contexts
                            ll = start
                            rr = end
                            while ll > 0 and not text[ll - 1].isspace() and text[ll - 1] not in "[]()<>":
                                ll -= 1
                            tlen2 = len(text)
                            while rr < tlen2 and not text[rr].isspace() and text[rr] not in "[]()<>":
                                rr += 1
                            tok2 = text[ll:rr].lower()
                            if (
                                "://" in tok2
                                or tok2.startswith("www.")
                                or re.search(r"\.[a-z]{2,15}(?:/|\b)", tok2)
                            ):
                                pos = idx + 1
                                continue
                            # For organization/location, also require at least one
                            # uppercase character in the original slice to reduce
                            # false positives from fragments and common words.
                            if (
                                getattr(self, "name", "") in {"organization", "location"}
                                and original_slice.islower()
                            ):
                                pos = idx + 1
                                continue
                            yield self.filth_cls(
                                beg=start,
                                end=end,
                                text=original_slice,
                                detector_name=self.name,
                                document_name=document_name,
                            )
                            matched_any = True
                    pos = idx + 1


class DutchEntityDetector(JSONEntityDetector):
    """Base class for Dutch entity detectors."""

    COMMON_WORDS = {
        "een",
        "het",
        "de",
        "die",
        "dat",
        "deze",
        "dit",
        "die",
        "dan",
        "toen",
        "als",
        "maar",
        "want",
        "dus",
        "nog",
        "al",
        "naar",
        "door",
        "om",
        "bij",
        "aan",
        "van",
        "in",
        "op",
        "te",
        "ten",
        "ter",
        "met",
        "tot",
        "voor",
        "ben",
        # Ambiguous Dutch words often mistaken for locations when lowercase
        "hoeven",  # verb/noun
        "velden",  # plural common noun
        "drie",  # number
        "halfweg",  # adverb/compound
        "heel",  # adverb
        "waarde",  # noun
        "zetten",  # verb
        "nuis",  # common token in context, lowercase only
        "leiden",  # verb; allow capitalized city name
    }
    data_subdir = "nl_entities"


class EnglishEntityDetector(JSONEntityDetector):
    """Base class for English entity detectors."""

    COMMON_WORDS = {
        "a",
        "an",
        "and",
        "at",
        "be",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "their",
        "there",
        "this",
        "to",
        "was",
        "were",
        "with",
    }
    data_subdir = "en_entities"
