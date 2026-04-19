import os
import psutil


def is_constrained_mode() -> bool:
    """True when available RAM < 6 GB or free disk < 1 GB."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(".")
    return mem.available < 6 * 1024**3 or disk.free < 1 * 1024**3


def get_max_image_width() -> int:
    """Max image width for VLM preprocessing based on available memory."""
    if is_constrained_mode():
        return 600
    return 800


def get_max_tokens() -> int:
    """Max token budget for VLM responses based on available memory."""
    if is_constrained_mode():
        return 100
    return 150


def get_max_retries() -> int:
    """Max retry attempts for low-confidence VLM responses."""
    return int(os.environ.get("SC_MAX_RETRIES", "3"))
