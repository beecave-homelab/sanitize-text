"""Dutch entity detectors."""

from scrubadub.detectors import register_detector
from ..filth import LocationFilth, OrganizationFilth, NameFilth
from .base import DutchEntityDetector

@register_detector
class DutchLocationDetector(DutchEntityDetector):
    """Detector for Dutch locations."""
    name = 'location'
    filth_cls = LocationFilth
    json_file = 'cities.json'

@register_detector
class DutchOrganizationDetector(DutchEntityDetector):
    """Detector for Dutch organizations."""
    name = 'organization'
    filth_cls = OrganizationFilth
    json_file = 'organizations.json'

@register_detector
class DutchNameDetector(DutchEntityDetector):
    """Detector for Dutch names."""
    name = 'name'
    filth_cls = NameFilth
    json_file = 'names.json' 