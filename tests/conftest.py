"""Test configuration: make the webapp package importable as `src.*`."""

import sys
from pathlib import Path

WEBAPP_DIR = Path(__file__).resolve().parent.parent / 'webapp'

if str(WEBAPP_DIR) not in sys.path:
    sys.path.insert(0, str(WEBAPP_DIR))
