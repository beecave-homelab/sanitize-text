"""Text scrubbing orchestration helpers.

This module builds `scrubadub` pipelines using the registered detector
catalogue and exposes helpers that return structured results for callers. The
implementation is intentionally data driven so new detectors can be added
without editing the control flow.
"""

from __future__ import annotations

import importlib.util as importlib_util
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    import scrubadub


logger = logging.getLogger(__name__)


DEFAULT_LOCALE = "nl_NL"


@dataclass(frozen=True)
class DetectorContext:
    """Context passed to detector factories.

    Attributes:
        locale: Locale identifier used to select locale-specific detectors.
    """

    locale: str


@dataclass(frozen=True)
class DetectorSpec:
    """Descriptor for a detector entry in the catalogue.

    Attributes:
        name: Canonical detector name.
        description: Human-readable summary of the detector.
        factory: Callable that builds the detector when requested.
        enabled: Optional predicate deciding whether the detector can run in a
            given context.
        enabled_by_default: Whether the detector participates when callers do
            not explicitly request a subset.
    """

    name: str
    description: str
    factory: Callable[[DetectorContext], scrubadub.detectors.Detector]
    enabled: Callable[[DetectorContext], bool] | None = None
    enabled_by_default: bool = True

    def is_enabled(self, context: DetectorContext) -> bool:
        """Return whether the detector is enabled in ``context``.

        Args:
            context: Context describing the current locale.

        Returns:
            bool: ``True`` when the detector should be available.
        """
        if self.enabled is None:
            return True
        return self.enabled(context)


@dataclass(frozen=True)
class ScrubOutcome:
    """Structured scrubbing result returned to callers.

    Attributes:
        texts: Scrubbed text keyed by locale.
        detectors: Detector names executed for each locale.
        errors: Error messages keyed by locale for failed runs.
    """

    texts: dict[str, str]
    detectors: dict[str, list[str]]
    errors: dict[str, str]


@dataclass(frozen=True)
class LocaleResult:
    """Scrubbing outcome for a single locale.

    Attributes:
        locale: Locale identifier.
        text: Scrubbed text for the locale.
        filth: Optional list of filth objects collected for the locale.
    """

    locale: str
    text: str
    filth: list[scrubadub.filth.Filth] | None = None


@dataclass(frozen=True)
class MultiLocaleResult:
    """Multi-locale scrubbing result for high-level callers.

    Attributes:
        results: Per-locale scrubbed text and optional filth.
        errors: Error messages keyed by locale for failed runs.
    """

    results: list[LocaleResult]
    errors: dict[str, str]


def _spacy_is_available() -> bool:
    """Return ``True`` when ``scrubadub-spacy`` is importable."""
    try:
        return importlib_util.find_spec("scrubadub_spacy.detectors") is not None
    except ModuleNotFoundError:
        return False


def _build_markdown_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import MarkdownUrlDetector

    return MarkdownUrlDetector()


def _build_sharepoint_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import SharePointUrlDetector

    return SharePointUrlDetector()


def _build_url_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import BareDomainDetector

    return BareDomainDetector()


def _build_email_detector(context: DetectorContext) -> scrubadub.detectors.Detector:
    from scrubadub.detectors.email import EmailDetector

    return EmailDetector(locale=context.locale)


def _build_phone_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from scrubadub.detectors.phone import PhoneDetector

    return PhoneDetector()


def _build_private_ip_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import PrivateIPDetector

    return PrivateIPDetector()


def _build_public_ip_detector(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import PublicIPDetector

    return PublicIPDetector()


def _build_dutch_location(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import DutchLocationDetector

    return DutchLocationDetector()


def _build_dutch_org(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import DutchOrganizationDetector

    return DutchOrganizationDetector()


def _build_dutch_name(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import DutchNameDetector

    return DutchNameDetector()


def _build_english_location(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import EnglishLocationDetector

    return EnglishLocationDetector()


def _build_english_org(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import EnglishOrganizationDetector

    return EnglishOrganizationDetector()


def _build_english_name(_: DetectorContext) -> scrubadub.detectors.Detector:
    from sanitize_text.utils.custom_detectors import EnglishNameDetector

    return EnglishNameDetector()


def _build_date_of_birth(_: DetectorContext) -> scrubadub.detectors.Detector:
    import scrubadub

    return scrubadub.detectors.DateOfBirthDetector()


_SPACY_MODELS = {
    "nl_NL": "nl_core_news_sm",
    "en_US": "en_core_web_sm",
}


def _build_spacy_detector(context: DetectorContext) -> scrubadub.detectors.Detector:
    from scrubadub_spacy.detectors import SpacyEntityDetector

    model = _SPACY_MODELS[context.locale]
    name = f"spacy_{context.locale.split('_')[0]}"
    return SpacyEntityDetector(model=model, name=name)


def _spacy_enabled(context: DetectorContext) -> bool:
    return context.locale in _SPACY_MODELS and _spacy_is_available()


GENERIC_DETECTORS: list[DetectorSpec] = [
    DetectorSpec(
        name="markdown_url",
        description="Detect URLs within Markdown links [text](url)",
        factory=_build_markdown_detector,
    ),
    DetectorSpec(
        name="sharepoint_url",
        description="Detect SharePoint URLs (runs before generic URL)",
        factory=_build_sharepoint_detector,
    ),
    DetectorSpec(
        name="url",
        description="Detect URLs (domains, www prefixes, http(s), complex paths, query params)",
        factory=_build_url_detector,
    ),
    DetectorSpec(
        name="email",
        description="Detect email addresses (e.g., user@example.com)",
        factory=_build_email_detector,
    ),
    DetectorSpec(
        name="phone",
        description="Detect phone numbers",
        factory=_build_phone_detector,
    ),
    DetectorSpec(
        name="private_ip",
        description="Detect private IP addresses (192.168.x.x, 10.0.x.x, 172.16-31.x.x)",
        factory=_build_private_ip_detector,
    ),
    DetectorSpec(
        name="public_ip",
        description="Detect public IP addresses (any non-private IP)",
        factory=_build_public_ip_detector,
    ),
]


LOCALE_DETECTORS: dict[str, list[DetectorSpec]] = {
    "nl_NL": [
        DetectorSpec(
            name="location",
            description="Detect Dutch locations (cities)",
            factory=_build_dutch_location,
        ),
        DetectorSpec(
            name="organization",
            description="Detect Dutch organization names",
            factory=_build_dutch_org,
        ),
        DetectorSpec(
            name="name",
            description="Detect Dutch person names",
            factory=_build_dutch_name,
        ),
        DetectorSpec(
            name="spacy_entities",
            description="Detect named entities using spaCy (requires sanitize-text[spacy])",
            factory=_build_spacy_detector,
            enabled=_spacy_enabled,
            enabled_by_default=False,
        ),
    ],
    "en_US": [
        DetectorSpec(
            name="name",
            description="Detect person names (English)",
            factory=_build_english_name,
        ),
        DetectorSpec(
            name="organization",
            description="Detect organization names (English)",
            factory=_build_english_org,
        ),
        DetectorSpec(
            name="location",
            description="Detect locations (English)",
            factory=_build_english_location,
        ),
        DetectorSpec(
            name="date_of_birth",
            description="Detect dates of birth",
            factory=_build_date_of_birth,
        ),
        DetectorSpec(
            name="spacy_entities",
            description="Detect named entities using spaCy (requires sanitize-text[spacy])",
            factory=_build_spacy_detector,
            enabled=_spacy_enabled,
            enabled_by_default=False,
        ),
    ],
}


def _iter_enabled_specs(
    specs: Iterable[DetectorSpec],
    context: DetectorContext,
) -> list[DetectorSpec]:
    """Return detector specs enabled for ``context``.

    Args:
        specs: Candidate detector specifications.
        context: Locale context used to evaluate optional predicates.

    Returns:
        list[DetectorSpec]: Enabled specifications preserving input order.
    """
    return [spec for spec in specs if spec.is_enabled(context)]


def get_generic_detector_descriptions(locale: str | None = None) -> dict[str, str]:
    """Return descriptions for generic detectors.

    Args:
        locale: Optional locale identifier used to check conditional
            availability. Defaults to :data:`DEFAULT_LOCALE` when omitted.

    Returns:
        dict[str, str]: Mapping of detector names to descriptions.
    """
    context = DetectorContext(locale=locale or DEFAULT_LOCALE)
    return {spec.name: spec.description for spec in _iter_enabled_specs(GENERIC_DETECTORS, context)}


def get_locale_detector_descriptions(locale: str) -> dict[str, str]:
    """Return descriptions for detectors specific to ``locale``.

    Args:
        locale: Locale identifier.

    Returns:
        dict[str, str]: Mapping of detector names to descriptions.
    """
    context = DetectorContext(locale=locale)
    return {
        spec.name: spec.description
        for spec in _iter_enabled_specs(LOCALE_DETECTORS.get(locale, []), context)
    }


def get_available_detectors(
    locale: str | None = None,
) -> dict[str, str] | dict[str, dict[str, str]]:
    """Return detector descriptions for ``locale`` or all locales.

    Args:
        locale: Optional locale identifier. When provided the result contains a
            single mapping for the requested locale; otherwise all locales are
            returned.

    Returns:
        dict[str, str] | dict[str, dict[str, str]]: Detector descriptions for
        either a single locale or every registered locale.
    """
    if locale:
        generic = get_generic_detector_descriptions(locale)
        locale_specific = get_locale_detector_descriptions(locale)
        combined: dict[str, str] = {**generic, **locale_specific}
        return combined

    return {loc: get_locale_detector_descriptions(loc) for loc in LOCALE_DETECTORS}


def setup_scrubber(
    locale: str,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
    verbose: bool = False,
    post_processor_factory: Callable[[], object] | None = None,
) -> scrubadub.Scrubber:
    """Return a configured scrubber for ``locale``.

    Args:
        locale: Locale code (for example ``"nl_NL"`` or ``"en_US"``).
        selected_detectors: Optional detector names to execute. When ``None``
            the default enabled detectors are used.
        custom_text: Optional custom text to treat as PII.
        verbose: Whether the detectors should expose verbose behaviour.
        post_processor_factory: Optional callable returning a post-processor
            instance. Defaults to :data:`DEFAULT_POST_PROCESSOR_FACTORY`, which
            creates :class:`sanitize_text.utils.post_processors.HashedPIIReplacer`.

    Returns:
        scrubadub.Scrubber: Scrubber instance ready to process text for the
        requested locale.
    """
    # Lazy imports to avoid heavy imports during CLI startup (e.g., --list-detectors)
    import scrubadub

    from sanitize_text.utils.custom_detectors import CustomWordDetector
    from sanitize_text.utils.custom_detectors.base import DutchEntityDetector
    from sanitize_text.utils.post_processors import DEFAULT_POST_PROCESSOR_FACTORY

    # Reset entity deduplication cache for new scrubber instance
    if locale == "nl_NL":
        DutchEntityDetector.reset_loaded_entities()

    detector_list: list[scrubadub.detectors.Detector] = []
    context = DetectorContext(locale=locale)
    generic_specs = _iter_enabled_specs(GENERIC_DETECTORS, context)
    locale_specs = _iter_enabled_specs(LOCALE_DETECTORS.get(locale, []), context)
    ordered_specs = (*generic_specs, *locale_specs)
    available_order = [spec.name for spec in ordered_specs]
    available_detectors = set(available_order)

    normalized_selection: list[str] | None = None
    if selected_detectors is not None:
        normalized_selection = [detector.lower() for detector in selected_detectors]
        invalid_detectors = [d for d in normalized_selection if d not in available_detectors]
        if invalid_detectors:
            logger.warning(
                "Invalid detector(s) for locale %s: %s",
                locale,
                ", ".join(sorted(set(invalid_detectors))),
            )
        normalized_selection = [
            detector for detector in normalized_selection if detector in available_detectors
        ]

    if normalized_selection is None:
        normalized_selection = [spec.name for spec in ordered_specs if spec.enabled_by_default]

    if custom_text:
        detector_list.append(CustomWordDetector(custom_text=custom_text))

    for spec in ordered_specs:
        if spec.name in normalized_selection:
            try:
                detector_list.append(spec.factory(context))
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Could not add detector %s: %s", spec.name, exc)

    factory = post_processor_factory or DEFAULT_POST_PROCESSOR_FACTORY
    post_processors = [factory()]

    scrubber = scrubadub.Scrubber(
        locale=locale,
        detector_list=detector_list,
        post_processor_list=post_processors,
    )

    scrubber.detectors = {detector.name: detector for detector in detector_list}

    # Store verbose flag on scrubber and propagate to all detectors
    scrubber._verbose = verbose  # type: ignore[attr-defined]
    for detector in detector_list:
        detector._verbose = verbose  # type: ignore[attr-defined]

    return scrubber


def run_multi_locale_scrub(
    *,
    text: str,
    locale: str | None,
    per_locale_detectors: dict[str, list[str]] | None = None,
    custom_text: str | None = None,
    cleanup: bool = True,
    cleanup_func: Callable[[str], str] | None = None,
    post_processor_factory: Callable[[], object] | None = None,
    verbose: bool = False,
    include_filth: bool = False,
) -> MultiLocaleResult:
    """Return scrubbed text (and optional filth) for the requested locale.

    This helper encapsulates the repeated pattern of multi-locale processing:
    building the locale list, constructing scrubbers, applying optional
    cleanup, and (optionally) collecting filth for inspection.
    """
    locales_to_process = [DEFAULT_LOCALE] if locale is None else [locale]
    results: list[LocaleResult] = []
    errors: dict[str, str] = {}

    for current_locale in locales_to_process:
        detectors_for_locale: list[str] | None = None
        if per_locale_detectors is not None:
            detectors_for_locale = per_locale_detectors.get(current_locale, [])
        try:
            scrubber = setup_scrubber(
                current_locale,
                detectors_for_locale,
                custom_text=custom_text,
                verbose=verbose,
                post_processor_factory=post_processor_factory,
            )
            scrubbed_text = scrubber.clean(text)
            if cleanup and cleanup_func is not None:
                scrubbed_text = cleanup_func(scrubbed_text)

            filths: list[scrubadub.filth.Filth] | None = None
            if include_filth:
                filth_map = collect_filth(
                    text,
                    locale=current_locale,
                    selected_detectors=detectors_for_locale,
                    custom_text=custom_text,
                )
                filths = filth_map.get(current_locale, [])

            results.append(
                LocaleResult(
                    locale=current_locale,
                    text=scrubbed_text,
                    filth=filths,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Processing failed for locale %s: %s", current_locale, exc)
            errors[current_locale] = str(exc)

    return MultiLocaleResult(results=results, errors=errors)


def scrub_text(
    text: str,
    locale: str | None = None,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
    verbose: bool = False,
) -> ScrubOutcome:
    """Return scrubbed text for each processed locale.

    Args:
        text: Raw text to scrub.
        locale: Optional locale identifier. When omitted, the default locale
            :data:`DEFAULT_LOCALE` is processed.
        selected_detectors: Optional list of detector names. When ``None`` the
            default detectors for each locale are used.
        custom_text: Optional custom text treated as PII.
        verbose: Whether detector implementations should run in verbose mode.

    Returns:
        ScrubOutcome: Structured result containing scrubbed text, detector
        metadata, and locale-specific errors.

    Raises:
        Exception: If every locale fails to process.
    """
    scrubbed_texts: dict[str, str] = {}
    detectors_by_locale: dict[str, list[str]] = {}
    errors: dict[str, str] = {}
    locales_to_process = [DEFAULT_LOCALE] if locale is None else [locale]
    for current_locale in locales_to_process:
        try:
            scrubber = setup_scrubber(current_locale, selected_detectors, custom_text, verbose)

            scrubbed_text = scrubber.clean(text)
            scrubbed_texts[current_locale] = scrubbed_text
            detectors_by_locale[current_locale] = list(scrubber.detectors.keys())
        except Exception as exc:
            logger.warning("Processing failed for locale %s: %s", current_locale, exc)
            errors[current_locale] = str(exc)
            continue

    if not scrubbed_texts:
        raise Exception("All processing attempts failed")
    return ScrubOutcome(texts=scrubbed_texts, detectors=detectors_by_locale, errors=errors)


def collect_filth(
    text: str,
    locale: str | None = None,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
) -> dict[str, list[scrubadub.filth.Filth]]:
    """Collect filth objects (with replacement strings) for the given text.

    Args:
        text: The text to analyse.
        locale: Optional locale (default: :data:`DEFAULT_LOCALE`).
        selected_detectors: Optional list of detectors.
        custom_text: Optional custom text.

    Returns:
        Mapping ``locale -> list[Filth]`` where each filth has
        ``replacement_string`` populated by post-processors.
    """
    from scrubadub import filth as _filth  # noqa: F401  # imported for typing only

    out: dict[str, list[scrubadub.filth.Filth]] = {}
    locales_to_process = [locale] if locale else [DEFAULT_LOCALE]

    for current_locale in locales_to_process:
        scrubber = setup_scrubber(current_locale, selected_detectors, custom_text)
        filths = list(scrubber.iter_filth(text))
        # Apply our HashedPIIReplacer explicitly to populate replacement_string
        from sanitize_text.utils.post_processors import HashedPIIReplacer

        replacer = HashedPIIReplacer()
        filths = replacer.process_filth(filths)
        out[current_locale] = filths
    return out
