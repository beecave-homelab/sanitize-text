"""Custom filth types for text sanitization.

This module defines custom filth types that represent different kinds of
personally identifiable information (PII) found in text.
"""

from scrubadub.filth import Filth
from scrubadub.filth.url import UrlFilth

class LocationFilth(Filth):
    """Filth subclass for geographical locations.
    
    This class represents detected location information in text,
    such as cities, towns, addresses, and other geographical references.
    """
    type = 'location'

class OrganizationFilth(Filth):
    """Filth subclass for organization names.
    
    This class represents detected organization information in text,
    such as company names, institutions, and other organizational entities.
    """
    type = 'organization'

class NameFilth(Filth):
    """Filth subclass for person names.
    
    This class represents detected personal names in text,
    including first names, last names, and full names.
    """
    type = 'name'

class PrivateIPFilth(Filth):
    """Filth subclass for private IP addresses.
    
    This class represents detected private IP addresses in text,
    including addresses in the ranges:
    - 10.0.0.0 to 10.255.255.255
    - 172.16.0.0 to 172.31.255.255
    - 192.168.0.0 to 192.168.255.255
    """
    type = 'private_ip'

class PublicIPFilth(Filth):
    """Filth subclass for public IP addresses.
    
    This class represents detected public IP addresses in text,
    which are any valid IPv4 addresses that are not in private IP ranges.
    These addresses are potentially sensitive as they can identify
    specific internet-connected devices or networks.
    """
    type = 'public_ip' 