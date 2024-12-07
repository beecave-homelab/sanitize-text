import re
import scrubadub
from scrubadub.detectors import RegexDetector
from scrubadub.filth import Filth


class PrivateIPFilth(Filth):
    """Custom Filth class for private IP addresses."""
    type = 'private_ip'


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

# Register the detector so it can be used with a Scrubber
scrubadub.detectors.register_detector(PrivateIPDetector, autoload=True)