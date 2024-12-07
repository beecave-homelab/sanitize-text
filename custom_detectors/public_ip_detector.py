import re
import scrubadub
from scrubadub.detectors import RegexDetector
from scrubadub.filth import Filth


class PublicIPFilth(Filth):
    """Custom Filth class for public IP addresses."""
    type = 'public_ip'


class PublicIPDetector(RegexDetector):
    """
    A custom detector to identify and redact public IP addresses from text.
    Public IP addresses are identified as any IP that does not fall within the following private IP ranges:
    - 192.168.X.X (65,024 IPs)
    - 10.0.X.X (65,024 IPs)
    - 172.16.0.0 to 172.31.255.255 (1,048,576 IPs)
    
    This detector will identify IPv4 addresses not within these private IP ranges.
    """
    name = 'public_ip'
    filth_cls = PublicIPFilth

    # Regex pattern for identifying public IP addresses
    regex = re.compile(
        r'\b(?!(?:192\.168|10\.0|172\.(?:1[6-9]|2[0-9]|3[0-1]))\.\d{1,3}\.\d{1,3})'  # Exclude private ranges
        r'(?:\d{1,3}\.){3}\d{1,3}\b'  # Match valid IPv4 addresses
    )

# Register the detector so it can be used with a Scrubber
scrubadub.detectors.register_detector(PublicIPDetector, autoload=True)