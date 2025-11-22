"""Base classes for custom detectors."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

import ahocorasick
from scrubadub.detectors import Detector

logger = logging.getLogger(__name__)


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
        # Build Aho-Corasick automaton for efficient multi-pattern matching
        self._automaton: ahocorasick.Automaton | None = None
        self._entity_map: dict[str, str] = {}  # lowercase -> original
        self._multi_word_entities: set[str] = set()
        self._build_automaton()

    def _load_json_entities(self) -> None:
        """Populate ``self.entities`` with matches from the JSON resource.

        Raises:
            ValueError: If ``data_subdir`` is not specified on the subclass.
        """
        if not self.data_subdir:
            raise ValueError("data_subdir must be defined for JSONEntityDetector subclasses")

        try:
            data_dir = Path(__file__).parent.parent.parent / "data" / self.data_subdir
            filepath = data_dir / self.json_file

            if not filepath.exists():
                logger.warning("Could not find entity file %s", self.json_file)
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
            logger.warning("Could not load JSON entity file %s: %s", self.json_file, exc)

    def _build_automaton(self) -> None:
        """Build Aho-Corasick automaton for efficient multi-pattern matching.

        The automaton enables O(n + m) matching where n is text length and m is
        the total length of all patterns, versus O(n × p) for individual regex
        searches where p is the number of patterns.
        """
        if not self.entities:
            return

        self._automaton = ahocorasick.Automaton()

        for entity in self.entities:
            # Store lowercase version for case-insensitive matching
            entity_lower = entity.lower()
            self._entity_map[entity_lower] = entity
            if " " in entity:
                self._multi_word_entities.add(entity_lower)

            # Add entity to automaton (case-insensitive)
            self._automaton.add_word(entity_lower, entity)

        # Build the automaton (this creates the failure links)
        self._automaton.make_automaton()

    def iter_filth(
        self,
        text: str,
        document_name: str | None = None,
    ) -> Iterator[object]:
        """Yield filth matches for any known entity occurrences in the text.

        Uses Aho-Corasick automaton for O(n) multi-pattern matching, then
        applies filters for word boundaries, common words, and URL contexts.
        """
        if not self._automaton:
            return

        # Check if verbose mode is enabled via scrubber
        verbose = getattr(self, "_verbose", False)

        if verbose:
            entity_count = len(self.entities)
            logger.info("  [%s] Searching for %d entities...", self.name, entity_count)

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

        # Unicode-safe letter pattern for word boundary checks
        letters_pattern = r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]"

        match_count = 0
        text_lower = text.lower()
        seen_matches: set[tuple[int, int]] = set()  # Track (start, end) to avoid duplicates

        # Single-pass search using Aho-Corasick automaton
        for end_idx, original_entity in self._automaton.iter(text_lower):
            # end_idx is 0-indexed position of last character of match
            start_idx = end_idx - len(original_entity) + 1
            matched_text = text[start_idx : end_idx + 1]

            # Skip if we've already yielded this exact match position
            if (start_idx, end_idx + 1) in seen_matches:
                continue

            # Word boundary check: match must not be inside a larger word
            if start_idx > 0 and re.match(letters_pattern, text[start_idx - 1]):
                continue
            if end_idx + 1 < len(text) and re.match(letters_pattern, text[end_idx + 1]):
                continue

            # Skip if match sits inside a URL or Markdown link
            l_pos = start_idx
            r_pos = end_idx + 1
            while l_pos > 0 and not text[l_pos - 1].isspace() and text[l_pos - 1] not in "[]()<>":
                l_pos -= 1
            while r_pos < len(text) and not text[r_pos].isspace() and text[r_pos] not in "[]()<>":
                r_pos += 1
            token = text[l_pos:r_pos].lower()
            if (
                "://" in token
                or token.startswith("www.")
                or re.search(r"\.[a-z]{2,15}(?:/|\b)", token)
            ):
                continue

            # For very short entities (<=3 chars), require capitalization
            if len(original_entity) <= 3 and matched_text.islower():
                continue

            # Skip lowercase stopwords (allow capitalized versions)
            if matched_text.islower() and matched_text.lower() in self.COMMON_WORDS:
                continue

            # For organization/location, require at least one uppercase letter
            if getattr(self, "name", "") in {"organization", "location"} and matched_text.islower():
                continue

            # Must contain at least one alphabetic character
            if not any(char.isalpha() for char in matched_text):
                continue

            seen_matches.add((start_idx, end_idx + 1))
            match_count += 1
            if verbose:
                logger.info("    ✓ Found: '%s' (%s)", matched_text, self.name)

            yield self.filth_cls(
                beg=start_idx,
                end=end_idx + 1,
                text=matched_text,
                detector_name=self.name,
                document_name=document_name,
            )

        # Fallback: normalization-aware search for multi-word entities
        # Handles cases like "Foo & Bar" matching "Foo en Bar" or zero-width chars
        if self._multi_word_entities:
            match_count_ref = [match_count]
            yield from self._search_normalized_entities(
                text=text,
                document_name=document_name,
                verbose=verbose,
                match_count_ref=match_count_ref,
                seen_matches=seen_matches,
            )
            match_count = match_count_ref[0]

        if verbose:
            logger.info("  [%s] Total matches: %d", self.name, match_count)

    def _search_normalized_entities(
        self,
        text: str,
        document_name: str | None,
        verbose: bool,
        match_count_ref: list[int],
        seen_matches: set[tuple[int, int]],
    ) -> Iterator[object]:
        """Fallback search for multi-word entities with normalization.

        Handles entities with zero-width characters, flexible whitespace,
        and '&' / '&amp;' variations (e.g., Dutch 'en' for '&').

        Yields:
            Filth objects for normalized entity matches.
        """

        def _strip_zw(s: str) -> str:
            return re.sub(r"[\u200b\u200c\u200d\u2060\u00AD]", "", s)

        def _collapse_ws(s: str) -> str:
            return re.sub(r"\s+", " ", s).strip()

        def _normalize_for_entity(s: str) -> str:
            s = _strip_zw(s)
            s = re.sub(r"&amp;|&", " en ", s, flags=re.IGNORECASE)
            s = _collapse_ws(s)
            return s.lower()

        norm_text = _normalize_for_entity(text)
        letters_pattern = r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]"

        for entity_lower in self._multi_word_entities:
            # Already matched via automaton, skip this expensive fallback
            if entity_lower in {text[s:e].lower() for s, e in seen_matches}:
                continue

            norm_entity = _normalize_for_entity(entity_lower)
            if len(norm_entity) < 5:  # Skip very short normalized entities
                continue

            pos = 0
            while True:
                idx = norm_text.find(norm_entity, pos)
                if idx == -1:
                    break

                # Map normalized position back to original text span
                start, end = self._map_normalized_span(
                    text=text,
                    norm_idx=idx,
                    norm_len=len(norm_entity),
                )

                if start is None or end is None or start >= end:
                    pos = idx + 1
                    continue

                # Skip if already matched
                if (start, end) in seen_matches:
                    pos = idx + 1
                    continue

                original_slice = text[start:end]

                # Apply same filters as main search
                if not any(char.isalpha() for char in original_slice):
                    pos = idx + 1
                    continue

                if "\n" in original_slice or "\r" in original_slice:
                    pos = idx + 1
                    continue

                # Word boundary check
                if start > 0 and re.match(letters_pattern, text[start - 1]):
                    pos = idx + 1
                    continue
                if end < len(text) and re.match(letters_pattern, text[end]):
                    pos = idx + 1
                    continue

                # Stopwords check
                if original_slice.strip().lower() in self.COMMON_WORDS:
                    pos = idx + 1
                    continue

                # URL/Markdown check
                ll = start
                rr = end
                while ll > 0 and not text[ll - 1].isspace() and text[ll - 1] not in "[]()<>":
                    ll -= 1
                while rr < len(text) and not text[rr].isspace() and text[rr] not in "[]()<>":
                    rr += 1
                tok2 = text[ll:rr].lower()
                if (
                    "://" in tok2
                    or tok2.startswith("www.")
                    or re.search(r"\.[a-z]{2,15}(?:/|\b)", tok2)
                ):
                    pos = idx + 1
                    continue

                # Organization/location capitalization check
                if (
                    getattr(self, "name", "") in {"organization", "location"}
                    and original_slice.islower()
                ):
                    pos = idx + 1
                    continue

                seen_matches.add((start, end))
                match_count_ref[0] += 1

                if verbose:
                    logger.info(
                        "    ✓ Found (normalized): '%s' (%s)",
                        original_slice,
                        self.name,
                    )

                yield self.filth_cls(
                    beg=start,
                    end=end,
                    text=original_slice,
                    detector_name=self.name,
                    document_name=document_name,
                )

                pos = idx + 1

    def _map_normalized_span(
        self,
        text: str,
        norm_idx: int,
        norm_len: int,
    ) -> tuple[int | None, int | None]:
        """Map a normalized text span back to original text positions.

        Args:
            text: Original text
            norm_idx: Start index in normalized text
            norm_len: Length in normalized text

        Returns:
            Tuple of (start_pos, end_pos) in original text, or (None, None) if invalid
        """
        tlen = len(text)
        j = 0
        norm_count = 0

        # Find start position in original text
        while j < tlen and norm_count < norm_idx:
            ch = text[j]
            if re.match(r"[\u200b\u200c\u200d\u2060\u00AD]", ch):
                j += 1
                continue
            if ch == "&":
                if text[j : j + 5].lower() == "&amp;":
                    norm_count += 3  # ' en'
                    j += 5
                else:
                    norm_count += 3
                    j += 1
                continue
            if ch.isspace():
                while j < tlen and text[j].isspace():
                    j += 1
                norm_count += 1
                continue
            norm_count += 1
            j += 1

        start = j

        # Find end position by consuming norm_len normalized characters
        norm_taken = 0
        while j < tlen and norm_taken < norm_len:
            ch = text[j]
            if re.match(r"[\u200b\u200c\u200d\u2060\u00AD]", ch):
                j += 1
                continue
            if text[j : j + 5].lower() == "&amp;":
                norm_taken += 3
                j += 5
                continue
            if ch == "&":
                norm_taken += 3
                j += 1
                continue
            if ch.isspace():
                while j < tlen and text[j].isspace():
                    j += 1
                norm_taken += 1
                continue
            norm_taken += 1
            j += 1

        end = j
        return (start, end) if start < end else (None, None)


class DutchEntityDetector(JSONEntityDetector):
    """Base class for Dutch entity detectors.

    Entities are deduplicated across detector types to prevent overlapping matches.
    Priority order: location > organization > name.
    """

    #: Shared set of entities already loaded by higher-priority detectors
    _dutch_loaded_entities: set[str] = set()

    def _load_json_entities(self) -> None:
        """Load entities while deduplicating across detector types."""
        super()._load_json_entities()
        # Filter out entities already loaded by higher-priority detectors
        original_count = len(self.entities)
        self.entities = [e for e in self.entities if e.lower() not in self._dutch_loaded_entities]
        # Track newly loaded entities for future detectors
        for entity in self.entities:
            self._dutch_loaded_entities.add(entity.lower())
        # Log filtering if significant
        removed = original_count - len(self.entities)
        if removed > 0:
            logger.info("  [%s] Filtered %d duplicate entities", self.name, removed)

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
        # Common words/fragments that cause false positives
        "loop",  # common word/UI element
        "mijlpaal",  # milestone
        "functioneel",  # functional (job title fragment)
        "beheerder",  # administrator (job title)
        "applicatiebeheerder",  # application administrator
        "medewerker",  # employee
        "collega",  # colleague
        "afdeling",  # department
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
