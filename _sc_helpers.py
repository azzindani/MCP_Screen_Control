"""Shared constants and imports for all _sc_* modules."""
from pathlib import Path

LMSTUDIO_BASE_URL = "http://localhost:1234/v1"

TMP_DIR = Path("tmp")
OBJECTIVE_PATH = TMP_DIR / "objective.md"
SCREEN_CURRENT = TMP_DIR / "screen_current.png"
SCREEN_PREV = TMP_DIR / "screen_prev.png"

MAX_IMAGE_WIDTH = 800
CONFIDENCE_THRESHOLD = 0.6
MAX_RETRIES = 3

__all__ = [
    "LMSTUDIO_BASE_URL",
    "TMP_DIR",
    "OBJECTIVE_PATH",
    "SCREEN_CURRENT",
    "SCREEN_PREV",
    "MAX_IMAGE_WIDTH",
    "CONFIDENCE_THRESHOLD",
    "MAX_RETRIES",
]
