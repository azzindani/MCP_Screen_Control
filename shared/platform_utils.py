"""Platform utilities — reads env at call time, never at import."""

import os


def is_constrained_mode() -> bool:
    """True when MCP_CONSTRAINED_MODE=1 or available RAM < 6 GB."""
    if os.environ.get("MCP_CONSTRAINED_MODE") == "1":
        return True
    try:
        import psutil

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(".")
        return mem.available < 6 * 1024**3 or disk.free < 1 * 1024**3
    except Exception:
        return False


def get_max_image_width() -> int:
    """Max image width for VLM preprocessing based on available memory."""
    return 600 if is_constrained_mode() else 800


def get_max_tokens() -> int:
    """Max token budget for VLM responses based on available memory."""
    return 100 if is_constrained_mode() else 150


def get_max_retries() -> int:
    """Max retry attempts for low-confidence VLM responses."""
    return int(os.environ.get("SC_MAX_RETRIES", "3"))
