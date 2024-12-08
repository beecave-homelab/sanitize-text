"""Custom Filth classes for text scrubbing."""

from scrubadub.filth import Filth
from scrubadub.filth.url import UrlFilth

class LocationFilth(Filth):
    """Filth class for location entities."""
    type = 'location'

class OrganizationFilth(Filth):
    """Filth class for organization entities."""
    type = 'organization'

class NameFilth(Filth):
    """Filth class for name entities."""
    type = 'name'

class PrivateIPFilth(Filth):
    """Custom Filth class for private IP addresses."""
    type = 'private_ip'

class PublicIPFilth(Filth):
    """Custom Filth class for public IP addresses."""
    type = 'public_ip' 