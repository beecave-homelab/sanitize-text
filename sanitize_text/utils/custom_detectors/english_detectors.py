"""English entity detectors for identifying common English PII."""

from scrubadub.detectors import register_detector

from ..filth import LocationFilth, NameFilth, OrganizationFilth
from .base import EnglishEntityDetector


@register_detector
class EnglishLocationDetector(EnglishEntityDetector):
    """Detector for English-language locations."""

    name = 'location'
    filth_cls = LocationFilth
    json_file = 'locations.json'


@register_detector
class EnglishOrganizationDetector(EnglishEntityDetector):
    """Detector for English-language organizations."""

    name = 'organization'
    filth_cls = OrganizationFilth
    json_file = 'organizations.json'


@register_detector
class EnglishNameDetector(EnglishEntityDetector):
    """Detector for English-language personal names."""

    name = 'name'
    filth_cls = NameFilth
    json_file = 'names.json'
