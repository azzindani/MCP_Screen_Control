"""Path resolution and atomic file writes."""

import os
import tempfile
from pathlib import Path


def resolve_path(path: str | Path, base: str | Path | None = None) -> Path:
    """Resolve path relative to base (default: cwd). Never escapes base."""
    p = Path(path)
    if p.is_absolute():
        return p
    root = Path(base) if base else Path.cwd()
    return (root / p).resolve()


def atomic_write_text(path: str | Path, content: str) -> None:
    """Write text content atomically using a temp file + rename."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dest.parent, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, dest)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# Backward-compatible alias
atomic_write = atomic_write_text
