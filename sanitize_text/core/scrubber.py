"""Core functionality for text scrubbing.

This module provides the main text scrubbing functionality, including setup of
detectors and text processing with multiple locales.
"""

from __future__ import annotations

import importlib.util as importlib_util
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
            "Detect URLs (bare domains, www prefixes,\n"
            "http(s), complex paths, query parameters)"
        ),
        "sharepoint_url": "Detect SharePoint URLs (runs before generic URL)",
        "markdown_url": "Detect URLs within Markdown links [text](url)",
        "private_ip": (
            "Detect private IP addresses (192.168.x.x, 10.0.x.x, 172.16-31.x.x)"
        ),
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
        spacy_available = importlib_util.find_spec(
            "scrubadub_spacy.detectors"
        ) is not None
    except ModuleNotFoundError:
        spacy_available = False

    if spacy_available:
        description = (
            "Detect named entities using spaCy (requires sanitize-text[spacy])"
        )
        locale_detectors["nl_NL"]["spacy_entities"] = description
        locale_detectors["en_US"]["spacy_entities"] = description

    if locale:
        return {**generic_detectors, **locale_detectors.get(locale, {})}
    return locale_detectors


def setup_scrubber(
    locale: str,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
    verbose: bool = False,
) -> scrubadub.Scrubber:
    """Set up a scrubber with appropriate detectors and post-processors.

    Args:
        locale: Locale code for text processing (e.g., 'nl_NL', 'en_US')
        selected_detectors: Optional list of detector names to use
        custom_text: Optional custom text to detect and replace
        verbose: Enable verbose logging of detector activity

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
        SharePointUrlDetector,
    )
    from sanitize_text.utils.custom_detectors.base import DutchEntityDetector
    from sanitize_text.utils.post_processors import HashedPIIReplacer

    # Reset entity deduplication cache for new scrubber instance
    if locale == "nl_NL":
        DutchEntityDetector._dutch_loaded_entities.clear()

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
        invalid_detectors = [
            d for d in normalized_selection if d not in available_detectors
        ]
        if invalid_detectors:
            print(
                f"Warning: Invalid detector(s) for locale {locale}:"
                f"{', '.join(invalid_detectors)}"
            )

    if normalized_selection is None:
        normalized_selection = available_order
        # Do not enable spaCy entities by default to reduce false positives.
        # Users can explicitly opt-in via --detectors spacy_entities
        if "spacy_entities" in normalized_selection:
            normalized_selection = [
                d for d in normalized_selection if d != "spacy_entities"
            ]

    if custom_text:
        detector_list.append(CustomWordDetector(custom_text=custom_text))

    # Use an ordered list to ensure markdown URL detection happens before plain URL
    detector_factories_ordered: list[tuple[str, Any]] = [
        ("markdown_url", MarkdownUrlDetector),
        ("sharepoint_url", SharePointUrlDetector),
        ("url", BareDomainDetector),
        ("email", lambda: EmailDetector(locale=locale)),
        ("phone", PhoneDetector),
        ("private_ip", PrivateIPDetector),
        ("public_ip", PublicIPDetector),
    ]

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

    for detector_name, factory in detector_factories_ordered:
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

    # Store verbose flag on scrubber and propagate to all detectors
    scrubber._verbose = verbose  # type: ignore[attr-defined]
    for detector in detector_list:
        detector._verbose = verbose  # type: ignore[attr-defined]

    return scrubber


def scrub_text(
    text: str,
    locale: str | None = None,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
    verbose: bool = False,
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
        verbose: Enable verbose logging of detector activity

    Returns:
        List of scrubbed texts, one for each processed locale

    Raises:
        Exception: If all processing attempts fail
    """
    import click

    scrubbed_texts: list[str] = []
    locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]
    for current_locale in locales_to_process:
        try:
            if verbose:
                click.echo(f"\n[Processing locale: {current_locale}]")
            scrubber = setup_scrubber(
                current_locale, selected_detectors, custom_text, verbose
            )

            if verbose:
                # Log active detectors
                detector_names = list(scrubber.detectors.keys())
                click.echo(f"[Active detectors: {', '.join(detector_names)}]")
                click.echo(f"[Scanning text ({len(text)} characters)...]\n")

            scrubbed_text = scrubber.clean(text)
            scrubbed_texts.append(f"Results for {current_locale}:\n{scrubbed_text}")

            if verbose:
                click.echo(f"\n[Completed processing for {current_locale}]")
        except Exception as exc:
            print(f"Warning: Processing failed for locale {current_locale}: {exc}")
            continue

    if not scrubbed_texts:
        raise Exception("All processing attempts failed")
    return scrubbed_texts


def collect_filth(
    text: str,
    locale: str | None = None,
    selected_detectors: list[str] | None = None,
    custom_text: str | None = None,
) -> dict[str, list[scrubadub.filth.Filth]]:
    """Collect filth objects (with replacement strings) for the given text.

    Args:
        text: The text to analyse.
        locale: Optional locale (default: both).
        selected_detectors: Optional list of detectors.
        custom_text: Optional custom text.

    Returns:
        Mapping ``locale -> list[Filth]`` where each filth has
        ``replacement_string`` populated by post-processors.
    """
    from scrubadub import filth as _filth  # noqa: F401  # imported for typing only

    out: dict[str, list[scrubadub.filth.Filth]] = {}
    locales_to_process = [locale] if locale else ["en_US", "nl_NL"]

    for current_locale in locales_to_process:
        scrubber = setup_scrubber(current_locale, selected_detectors, custom_text)
        filths = list(scrubber.iter_filth(text))
        # Apply our HashedPIIReplacer explicitly to populate replacement_string
        from sanitize_text.utils.post_processors import HashedPIIReplacer

        replacer = HashedPIIReplacer()
        filths = replacer.process_filth(filths)
        out[current_locale] = filths
    return out
