"""
Module to hold some top-level constants
"""

import os
from pathlib import Path
from datetime import datetime

# an absolute locator to the top level of the project for use as a navigation aid in other modules
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ROOT = PROJECT_ROOT / f"output/{datetime.now().strftime('%Y_%m_%d_%H%Mh')}"
