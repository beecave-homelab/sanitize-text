"""Dutch entity detectors for identifying Dutch locations, organizations, and names."""

from scrubadub.detectors import register_detector
from ..filth import LocationFilth, OrganizationFilth, NameFilth
from .base import DutchEntityDetector

@register_detector
class DutchLocationDetector(DutchEntityDetector):
    """Detector for Dutch locations.
    
    This detector identifies Dutch cities, towns, and other geographical locations
    using a predefined list loaded from cities.json. It inherits common Dutch
    word filtering and entity detection logic from DutchEntityDetector.
    """
    name = 'location'
    filth_cls = LocationFilth
    json_file = 'cities.json'

@register_detector
class DutchOrganizationDetector(DutchEntityDetector):
    """Detector for Dutch organizations.
    
    This detector identifies Dutch company names, institutions, and other organizations
    using a predefined list loaded from organizations.json. It inherits common Dutch
    word filtering and entity detection logic from DutchEntityDetector.
    """
    name = 'organization'
    filth_cls = OrganizationFilth
    json_file = 'organizations.json'

@register_detector
class DutchNameDetector(DutchEntityDetector):
    """Detector for Dutch names.
    
    This detector identifies Dutch personal names using a predefined list loaded
    from names.json. It inherits common Dutch word filtering and entity detection
    logic from DutchEntityDetector.
    """
    name = 'name'
    filth_cls = NameFilth
    json_file = 'names.json' 