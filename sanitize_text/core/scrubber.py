"""Core functionality for text scrubbing.

This module provides the main text scrubbing functionality, including setup of
detectors and text processing with multiple locales.
"""

from __future__ import annotations

import importlib.util as importlib_util
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - for type hints only
    import scrubadub


def get_available_detectors(locale: str | None = None) -> dict[str, str]:
    """Get available detector names and descriptions for the given locale.

    Args:
        locale: Optional locale code (e.g., 'nl_NL', 'en_US')

    Returns:
        Dictionary mapping detector names to their descriptions
    """
    generic_detectors = {
        "email": "Detect email addresses (e.g., user@example.com)",
        "phone": "Detect phone numbers",
        "url": (
            "Detect URLs (bare domains, www prefixes, http(s), complex paths, query parameters)"
        ),
        "markdown_url": "Detect URLs within Markdown links [text](url)",
        "private_ip": ("Detect private IP addresses (192.168.x.x, 10.0.x.x, 172.16-31.x.x)"),
        "public_ip": "Detect public IP addresses (any non-private IP)",
    }

    locale_detectors: dict[str, dict[str, str]] = {
        "nl_NL": {
            "location": "Detect Dutch locations (cities)",
            "organization": "Detect Dutch organization names",
            "name": "Detect Dutch person names",
        },
        "en_US": {
            "name": "Detect person names (English)",
            "organization": "Detect organization names (English)",
            "location": "Detect locations (English)",
            "date_of_birth": "Detect dates of birth",
        },
    }

    # Detect availability of spaCy-based detector without importing heavy modules
    try:
        spacy_available = importlib_util.find_spec("scrubadub_spacy.detectors") is not None
    except ModuleNotFoundError:
        spacy_available = False

    if spacy_available:
        description = "Detect named entities using spaCy (requires sanitize-text[spacy])"
        locale_detectors["nl_NL"]["spacy_entities"] = description
        locale_detectors["en_US"]["spacy_entities"] = description

    if locale:
        return {**generic_detectors, **locale_detectors.get(locale, {})}
    return locale_detectors


def setup_scrubber(
    locale: str,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
) -> scrubadub.Scrubber:
    """Set up a scrubber with appropriate detectors and post-processors.

    Args:
        locale: Locale code for text processing (e.g., 'nl_NL', 'en_US')
        selected_detectors: Optional list of detector names to use
        custom_text: Optional custom text to detect and replace

    Returns:
        Configured scrubber instance ready for text processing
    """
    # Lazy imports to avoid heavy imports during CLI startup (e.g., --list-detectors)
    import scrubadub
    from scrubadub.detectors.email import EmailDetector
    from scrubadub.detectors.phone import PhoneDetector

    from sanitize_text.utils.custom_detectors import (
        BareDomainDetector,
        CustomWordDetector,
        DutchLocationDetector,
        DutchNameDetector,
        DutchOrganizationDetector,
        EnglishLocationDetector,
        EnglishNameDetector,
        EnglishOrganizationDetector,
        MarkdownUrlDetector,
        PrivateIPDetector,
        PublicIPDetector,
    )
    from sanitize_text.utils.post_processors import HashedPIIReplacer

    try:  # pragma: no cover - optional dependency
        from scrubadub_spacy.detectors import (  # type: ignore
            SpacyEntityDetector as _SpacyEntityDetector,
        )

        spacy_entity_detector_cls = _SpacyEntityDetector
    except Exception:  # noqa: BLE001 - we only care about availability
        spacy_entity_detector_cls = None  # type: ignore[assignment]

    detector_list: list[scrubadub.detectors.Detector] = []
    available_order = list(get_available_detectors(locale).keys())
    available_detectors = set(available_order)

    normalized_selection: list[str] | None = None
    if selected_detectors:
        normalized_selection = [detector.lower() for detector in selected_detectors]
        invalid_detectors = [d for d in normalized_selection if d not in available_detectors]
        if invalid_detectors:
            print(
                f"Warning: Invalid detector(s) for locale {locale}: {', '.join(invalid_detectors)}"
            )

    if normalized_selection is None:
        normalized_selection = available_order

    if custom_text:
        detector_list.append(CustomWordDetector(custom_text=custom_text))

    detector_factories: dict[str, Any] = {
        "email": lambda: EmailDetector(locale=locale),
        "phone": PhoneDetector,
        "url": BareDomainDetector,
        "markdown_url": MarkdownUrlDetector,
        "private_ip": PrivateIPDetector,
        "public_ip": PublicIPDetector,
    }

    locale_factories: dict[str, dict[str, Any]] = {
        "nl_NL": {
            "location": DutchLocationDetector,
            "organization": DutchOrganizationDetector,
            "name": DutchNameDetector,
        },
        "en_US": {
            "location": EnglishLocationDetector,
            "organization": EnglishOrganizationDetector,
            "name": EnglishNameDetector,
            "date_of_birth": scrubadub.detectors.DateOfBirthDetector,
        },
    }

    if spacy_entity_detector_cls is not None:
        locale_factories.setdefault("nl_NL", {})["spacy_entities"] = (
            lambda: spacy_entity_detector_cls(model="nl_core_news_sm", name="spacy_nl")
        )
        locale_factories.setdefault("en_US", {})["spacy_entities"] = (
            lambda: spacy_entity_detector_cls(model="en_core_web_sm", name="spacy_en")
        )

    for detector_name, factory in detector_factories.items():
        if detector_name in normalized_selection:
            try:
                detector_list.append(factory())
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Could not add detector {detector_name}: {exc}")

    for detector_name, factory in locale_factories.get(locale, {}).items():
        if detector_name in normalized_selection:
            try:
                detector_list.append(factory())
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Could not add detector {detector_name}: {exc}")

    scrubber = scrubadub.Scrubber(
        locale=locale,
        detector_list=detector_list,
        post_processor_list=[HashedPIIReplacer()],
    )

    scrubber.detectors = {detector.name: detector for detector in detector_list}

    return scrubber


def scrub_text(
    text: str,
    locale: str | None = None,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
) -> list[str]:
    """Scrub PII from the given text using specified locale and detectors.

    This is the main function for text sanitization. It processes the input text
    using the specified locale and detectors, removing personally identifiable
    information (PII) and replacing it with anonymized placeholders.

    Args:
        text: The text to scrub
        locale: Optional locale code (e.g., 'nl_NL', 'en_US')
        selected_detectors: Optional list of detector names to use
        custom_text: Optional custom text to detect and replace

    Returns:
        List of scrubbed texts, one for each processed locale

    Raises:
        Exception: If all processing attempts fail
    """
    # Suppress specific warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="scrubadub")
    warnings.filterwarnings("ignore", category=FutureWarning, module="thinc")
    scrubbed_texts: list[str] = []
    locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]
    for current_locale in locales_to_process:
        try:
            scrubber = setup_scrubber(current_locale, selected_detectors, custom_text)
            scrubbed_text = scrubber.clean(text)
            scrubbed_texts.append(f"Results for {current_locale}:\n{scrubbed_text}")
        except Exception as exc:
            print(f"Warning: Processing failed for locale {current_locale}: {exc}")
            continue

    if not scrubbed_texts:
        raise Exception("All processing attempts failed")
    return scrubbed_texts
