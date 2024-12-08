"""IP address detectors."""

import re
from scrubadub.detectors import RegexDetector, register_detector
from ..filth import PrivateIPFilth, PublicIPFilth

@register_detector
class PrivateIPDetector(RegexDetector):
    """
    A custom detector to identify and redact private IP addresses from text.
    The following IP ranges are detected:
    - 192.168.X.X (65,024 IPs)
    - 10.0.X.X (65,024 IPs)
    - 172.X.X.X (1,048,576 IPs)
    """
    name = 'private_ip'
    filth_cls = PrivateIPFilth

    # Compile the regex pattern to match the IP ranges
    regex = re.compile(
        r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.0\.\d{1,3}\.\d{1,3}|172\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
    )

@register_detector
class PublicIPDetector(RegexDetector):
    """
    A custom detector to identify and redact public IP addresses from text.
    Public IP addresses are identified as any IP that does not fall within the following private IP ranges:
    - 192.168.X.X (65,024 IPs)
    - 10.0.X.X (65,024 IPs)
    - 172.16.0.0 to 172.31.255.255 (1,048,576 IPs)
    """
    name = 'public_ip'
    filth_cls = PublicIPFilth

    # Regex pattern for identifying public IP addresses
    regex = re.compile(
        r'\b(?!(?:192\.168|10\.0|172\.(?:1[6-9]|2[0-9]|3[0-1]))\.\d{1,3}\.\d{1,3})'  # Exclude private ranges
        r'(?:\d{1,3}\.){3}\d{1,3}\b'  # Match valid IPv4 addresses
    ) 