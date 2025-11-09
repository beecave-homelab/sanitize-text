"""Pytest configuration to ensure project root is on `sys.path`.

This allows test modules to import the in-tree `sanitize_text` package without
requiring an editable install. It keeps the test environment lightweight and
independent of PDM/virtual-env specifics.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repository root to import path (tests reside in ./tests)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
