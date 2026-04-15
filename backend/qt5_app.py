"""Compatibility launcher.

Use main.py at repository root as the primary entrypoint.
"""

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import run  # noqa: E402


if __name__ == "__main__":
    sys.exit(run())
