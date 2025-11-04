"""Web routes and API endpoints for the text sanitization web interface."""

from __future__ import annotations

from flask import Flask, Response, jsonify, render_template, request

from sanitize_text.core.scrubber import get_available_detectors, setup_scrubber

GENERIC_DETECTORS = {
    "email",
    "phone",
    "url",
    "markdown_url",
    "private_ip",
    "public_ip",
}


def _group_detectors() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return dictionaries of generic, English, and Dutch detectors."""
    english = get_available_detectors("en_US")
    dutch = get_available_detectors("nl_NL")

    generic = {key: english[key] for key in GENERIC_DETECTORS if key in english}
    english_specific = {
        key: value for key, value in english.items() if key not in GENERIC_DETECTORS
    }
    dutch_specific = {key: value for key, value in dutch.items() if key not in GENERIC_DETECTORS}

    return generic, english_specific, dutch_specific


def _build_locale_selections(
    selected_detectors: list[str] | None,
) -> dict[str, list[str]] | None:
    """Transform raw checkbox values into per-locale detector selections.

    Returns:
        Mapping from locale code to a sorted list of detector names, or ``None``
        if no selections were provided.
    """
    if not selected_detectors:
        return None

    generic_selection = {token for token in selected_detectors if ":" not in token}
    locale_map = {
        "en_US": set(generic_selection),
        "nl_NL": set(generic_selection),
    }

    for token in selected_detectors:
        if ":" not in token:
            continue
        prefix, _, detector_name = token.partition(":")
        if prefix == "en":
            locale_map["en_US"].add(detector_name)
        elif prefix == "nl":
            locale_map["nl_NL"].add(detector_name)

    return {locale: sorted(detectors) for locale, detectors in locale_map.items()}


def init_routes(app: Flask) -> Flask:
    """Initialize Flask routes for the web interface.

    Returns:
        The Flask application with routes registered.
    """
    generic_detectors, english_detectors, dutch_detectors = _group_detectors()
    spacy_available = "spacy_entities" in english_detectors or "spacy_entities" in dutch_detectors

    @app.route("/")
    def index() -> str:
        """Render the main page of the web interface.

        Returns:
            Rendered HTML for the index page.
        """
        return render_template(
            "index.html",
            generic_detectors=generic_detectors,
            english_detectors=english_detectors,
            dutch_detectors=dutch_detectors,
            spacy_available=spacy_available,
        )

    @app.route("/process", methods=["POST"])
    def process() -> Response:
        """Process text and remove PII based on specified locale and detectors.

        Returns:
            A JSON response with processing results or an error message.
        """
        data = request.json or {}
        input_text = data.get("text", "")
        locale = data.get("locale") or None
        selected_detectors = data.get("detectors") or []

        if not input_text:
            return jsonify({"error": "No text provided"}), 400

        per_locale_selection = _build_locale_selections(selected_detectors)
        locales_to_process = ["en_US", "nl_NL"] if locale is None else [locale]

        results = []
        for current_locale in locales_to_process:
            try:
                detectors_for_locale = None
                if per_locale_selection is not None:
                    detectors_for_locale = per_locale_selection.get(current_locale, [])
                scrubber = setup_scrubber(current_locale, detectors_for_locale)
                scrubbed_text = scrubber.clean(input_text)
                results.append({"locale": current_locale, "text": scrubbed_text})
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Warning: Processing failed for locale {current_locale}: {exc}")
                continue

        if not results:
            return jsonify({"error": "All processing attempts failed"}), 500

        return jsonify({"results": results})

    return app
